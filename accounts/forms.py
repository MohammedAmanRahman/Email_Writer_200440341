from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    """User registration form with styled Bootstrap 5 widgets."""

    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email address",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            "username": "Choose a username",
            "email": "Email address",
            "first_name": "First name",
            "last_name": "Last name",
            "password1": "Create a password",
            "password2": "Confirm your password",
        }

        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "")
            if "form-control" not in field.widget.attrs["class"]:
                field.widget.attrs["class"] = "form-control"
            field.widget.attrs["placeholder"] = placeholders.get(
                field_name, field.label or field_name.replace("_", " ").title()
            )


class LoginForm(AuthenticationForm):
    """Login form with styled Bootstrap 5 widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Password"}
        )
