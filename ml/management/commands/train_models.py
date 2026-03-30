"""
Django management command: train_models

Trains LSTM and/or MLP classifiers on CFPB complaint data,
prints per-epoch progress (loss, accuracy), computes comparison
metrics, and saves the best model to ml/trained_models/.

Usage:
    python manage.py train_models
    python manage.py train_models --epochs 30 --batch-size 128 --model lstm
"""
import json
import time
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from django.core.management.base import BaseCommand
from django.conf import settings

from ml.classifier import (
    LSTMClassifier,
    MLPClassifier,
    TextPreprocessor,
    DEFAULT_CONFIG,
)


class Command(BaseCommand):
    help = "Train LSTM and/or MLP classifiers on CFPB complaint data."

    # ------------------------------------------------------------------ #
    #  CLI arguments
    # ------------------------------------------------------------------ #

    def add_arguments(self, parser):
        parser.add_argument(
            "--epochs",
            type=int,
            default=DEFAULT_CONFIG["epochs"],
            help="Number of training epochs (default: %(default)s)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=DEFAULT_CONFIG["batch_size"],
            help="Batch size (default: %(default)s)",
        )
        parser.add_argument(
            "--model",
            type=str,
            choices=["lstm", "mlp", "both"],
            default="both",
            help="Which model(s) to train (default: both)",
        )

    # ------------------------------------------------------------------ #
    #  Entry point
    # ------------------------------------------------------------------ #

    def handle(self, *args, **options):
        epochs = options["epochs"]
        batch_size = options["batch_size"]
        model_choice = options["model"]

        self.stdout.write(self.style.SUCCESS(
            f"Training config: epochs={epochs}, batch_size={batch_size}, model={model_choice}"
        ))

        # ---- 1. Load data -------------------------------------------- #
        texts, labels, categories = self._load_data()
        if not texts:
            self.stderr.write(self.style.ERROR("No complaint data found. Aborting."))
            return

        num_classes = len(categories)
        self.stdout.write(f"Loaded {len(texts)} complaints across {num_classes} categories.")

        # ---- 2. Preprocess ------------------------------------------- #
        preprocessor = TextPreprocessor(
            vocab_size=DEFAULT_CONFIG["vocab_size"],
            max_length=DEFAULT_CONFIG["max_length"],
        )
        preprocessor.fit(texts)
        encoded = preprocessor.encode_batch(texts)
        label_tensor = torch.tensor(labels, dtype=torch.long)

        # ---- 3. Train / Val / Test split (70/15/15) ------------------ #
        n = len(texts)
        indices = torch.randperm(n)
        train_end = int(0.70 * n)
        val_end = int(0.85 * n)

        train_idx = indices[:train_end]
        val_idx = indices[train_end:val_end]
        test_idx = indices[val_end:]

        train_ds = TensorDataset(encoded[train_idx], label_tensor[train_idx])
        val_ds = TensorDataset(encoded[val_idx], label_tensor[val_idx])
        test_ds = TensorDataset(encoded[test_idx], label_tensor[test_idx])

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size)
        test_loader = DataLoader(test_ds, batch_size=batch_size)

        self.stdout.write(
            f"Split: train={len(train_ds)}, val={len(val_ds)}, test={len(test_ds)}"
        )

        # ---- 4. Train models ----------------------------------------- #
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.stdout.write(f"Device: {device}")

        results = {}

        if model_choice in ("lstm", "both"):
            self.stdout.write(self.style.SUCCESS("\n=== Training LSTM Classifier ==="))
            lstm_model = LSTMClassifier(
                vocab_size=DEFAULT_CONFIG["vocab_size"],
                embedding_dim=DEFAULT_CONFIG["embedding_dim"],
                hidden_dim=DEFAULT_CONFIG["hidden_dim"],
                output_dim=num_classes,
                n_layers=DEFAULT_CONFIG["n_layers"],
                dropout=DEFAULT_CONFIG["dropout"],
                bidirectional=DEFAULT_CONFIG["bidirectional"],
            ).to(device)
            results["lstm"] = self._train_and_evaluate(
                lstm_model, train_loader, val_loader, test_loader,
                epochs, device, "LSTM", num_classes,
            )

        if model_choice in ("mlp", "both"):
            self.stdout.write(self.style.SUCCESS("\n=== Training MLP Classifier ==="))
            mlp_model = MLPClassifier(
                vocab_size=DEFAULT_CONFIG["vocab_size"],
                embedding_dim=DEFAULT_CONFIG["embedding_dim"],
                hidden_dim=DEFAULT_CONFIG["hidden_dim"],
                output_dim=num_classes,
                dropout=DEFAULT_CONFIG["dropout"],
            ).to(device)
            results["mlp"] = self._train_and_evaluate(
                mlp_model, train_loader, val_loader, test_loader,
                epochs, device, "MLP", num_classes,
            )

        # ---- 5. Compare & save --------------------------------------- #
        if model_choice == "both" and "lstm" in results and "mlp" in results:
            self._print_comparison(results)

        # Determine best model
        best_name = model_choice
        if model_choice == "both":
            if results["lstm"]["test_accuracy"] >= results["mlp"]["test_accuracy"]:
                best_name = "lstm"
            else:
                best_name = "mlp"

        best = results[best_name]
        self.stdout.write(self.style.SUCCESS(
            f"\nBest model: {best_name.upper()} "
            f"(test accuracy: {best['test_accuracy']:.4f})"
        ))

        # Save
        self._save_model(best["model"], best_name, preprocessor, categories)
        self.stdout.write(self.style.SUCCESS("Models and artefacts saved."))

    # ------------------------------------------------------------------ #
    #  Data loading
    # ------------------------------------------------------------------ #

    def _load_data(self):
        """Load complaint data from CFPBComplaint model."""
        from complaints.models import CFPBComplaint

        qs = CFPBComplaint.objects.exclude(
            complaint_narrative__exact=""
        ).exclude(
            product__exact=""
        ).values_list("complaint_narrative", "product")

        texts = []
        raw_labels = []
        for narrative, product in qs.iterator():
            texts.append(narrative)
            raw_labels.append(product)

        if not texts:
            return [], [], []

        # Build category mapping
        unique_cats = sorted(set(raw_labels))
        cat2idx = {c: i for i, c in enumerate(unique_cats)}
        labels = [cat2idx[c] for c in raw_labels]

        return texts, labels, unique_cats

    # ------------------------------------------------------------------ #
    #  Training loop
    # ------------------------------------------------------------------ #

    def _train_and_evaluate(self, model, train_loader, val_loader,
                            test_loader, epochs, device, name, num_classes):
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(
            model.parameters(), lr=DEFAULT_CONFIG["learning_rate"]
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", patience=3, factor=0.5
        )

        best_val_loss = float("inf")
        best_state = None

        for epoch in range(1, epochs + 1):
            t0 = time.time()

            # -- Train ------------------------------------------------- #
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            for X_batch, y_batch in train_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()
                output = model(X_batch)
                loss = criterion(output, y_batch)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                train_loss += loss.item() * X_batch.size(0)
                preds = output.argmax(dim=1)
                train_correct += (preds == y_batch).sum().item()
                train_total += X_batch.size(0)

            train_loss /= train_total
            train_acc = train_correct / train_total

            # -- Validate ---------------------------------------------- #
            val_loss, val_acc = self._evaluate(model, val_loader, criterion, device)
            scheduler.step(val_loss)

            elapsed = time.time() - t0
            self.stdout.write(
                f"[{name}] Epoch {epoch:3d}/{epochs} | "
                f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
                f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} | "
                f"{elapsed:.1f}s"
            )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        # Restore best checkpoint
        if best_state:
            model.load_state_dict(best_state)
            model.to(device)

        # -- Test ------------------------------------------------------ #
        test_loss, test_acc = self._evaluate(model, test_loader, criterion, device)
        self.stdout.write(self.style.SUCCESS(
            f"[{name}] Test Loss: {test_loss:.4f} Acc: {test_acc:.4f}"
        ))

        # Per-class metrics
        precision, recall, f1 = self._class_metrics(
            model, test_loader, device, num_classes
        )

        return {
            "model": model,
            "test_loss": test_loss,
            "test_accuracy": test_acc,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    # ------------------------------------------------------------------ #
    #  Evaluation helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _evaluate(model, loader, criterion, device):
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for X_batch, y_batch in loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                output = model(X_batch)
                loss = criterion(output, y_batch)
                total_loss += loss.item() * X_batch.size(0)
                preds = output.argmax(dim=1)
                correct += (preds == y_batch).sum().item()
                total += X_batch.size(0)
        if total == 0:
            return 0.0, 0.0
        return total_loss / total, correct / total

    @staticmethod
    def _class_metrics(model, loader, device, num_classes):
        """Compute macro-averaged precision, recall, F1."""
        model.eval()
        tp = np.zeros(num_classes)
        fp = np.zeros(num_classes)
        fn = np.zeros(num_classes)

        with torch.no_grad():
            for X_batch, y_batch in loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                preds = model(X_batch).argmax(dim=1).cpu().numpy()
                truth = y_batch.cpu().numpy()
                for c in range(num_classes):
                    tp[c] += ((preds == c) & (truth == c)).sum()
                    fp[c] += ((preds == c) & (truth != c)).sum()
                    fn[c] += ((preds != c) & (truth == c)).sum()

        precision_per = tp / (tp + fp + 1e-8)
        recall_per = tp / (tp + fn + 1e-8)
        f1_per = 2 * precision_per * recall_per / (precision_per + recall_per + 1e-8)

        precision = float(precision_per.mean())
        recall = float(recall_per.mean())
        f1 = float(f1_per.mean())
        return precision, recall, f1

    # ------------------------------------------------------------------ #
    #  Comparison output
    # ------------------------------------------------------------------ #

    def _print_comparison(self, results):
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("  Model Comparison"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        header = f"{'Metric':<20} {'LSTM':>12} {'MLP':>12}"
        self.stdout.write(header)
        self.stdout.write("-" * 46)

        for metric in ("test_accuracy", "precision", "recall", "f1", "test_loss"):
            lstm_val = results["lstm"][metric]
            mlp_val = results["mlp"][metric]
            self.stdout.write(
                f"{metric:<20} {lstm_val:>12.4f} {mlp_val:>12.4f}"
            )
        self.stdout.write("=" * 60)

    # ------------------------------------------------------------------ #
    #  Save artefacts
    # ------------------------------------------------------------------ #

    def _save_model(self, model, name, preprocessor, categories):
        model_dir = Path(settings.ML_MODEL_DIR)
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save model weights
        save_name = f"{name}_classifier.pt"
        torch.save(model.state_dict(), str(model_dir / save_name))

        # Also save as the default name if this is the best
        if name == "lstm":
            torch.save(model.state_dict(), str(model_dir / "lstm_classifier.pt"))

        # Vocabulary
        preprocessor.save(str(model_dir / "vocab.json"))

        # Categories
        with open(model_dir / "categories.json", "w") as f:
            json.dump(categories, f, indent=2)

        self.stdout.write(f"Saved: {model_dir / save_name}")
        self.stdout.write(f"Saved: {model_dir / 'vocab.json'}")
        self.stdout.write(f"Saved: {model_dir / 'categories.json'}")
