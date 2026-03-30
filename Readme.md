Can download data to put into ...\data\ from:
https://www.consumerfinance.gov/data-research/consumer-complaints/#get-the-data

# Consumer Complaint Assistant - Technical Report

## Table of Contents

1. [Overview](#1-overview)
2. [How the System Works (User Perspective)](#2-how-the-system-works-user-perspective)
3. [System Architecture](#3-system-architecture)
4. [The Web Application (Web Development Module)](#4-the-web-application-web-development-module)
5. [The Machine Learning Pipeline (Neural Networks Module)](#5-the-machine-learning-pipeline-neural-networks-module)
6. [The Data Mining Engine (Data Mining Module)](#6-the-data-mining-engine-data-mining-module)
7. [Security Implementation (Security Engineering Module)](#7-security-implementation-security-engineering-module)
8. [The Training System](#8-the-training-system)
9. [The Letter Generation System](#9-the-letter-generation-system)
10. [Database Design](#10-database-design)
11. [File Structure](#11-file-structure)
12. [How to Set Up and Run](#12-how-to-set-up-and-run)
13. [Technologies Used](#13-technologies-used)

---

## 1. Overview

The Consumer Complaint Assistant is a web application that helps users write formal complaint letters. Instead of the user having to know how to write a professional complaint, they simply describe their problem in plain language. The system then:

- **Classifies** what type of complaint it is (telecoms, retail, property, etc.)
- **Analyses** how negative or urgent the complaint sounds
- **Extracts** key details like the company name, product, and how long the problem has lasted
- **Finds** the most effective complaint strategy based on similar past complaints
- **Generates** a professionally written complaint letter as a downloadable PDF

The system improves over time. Users can feed it real complaint letters, and it learns from them to produce better letters in the future. It also provides a dashboard showing patterns and trends across all complaints.

---

## 2. How the System Works (User Perspective)

### Step 1: The User Submits a Complaint

The user visits the website, logs in, and navigates to "New Complaint". They see a form with three fields:

- **Complaint Details** - A text box where they describe their problem in their own words (e.g., "My broadband has been down for 3 days and BT won't fix it")
- **Company Name** - Optional text field for the company they're complaining about
- **Product/Service** - A dropdown menu with common options like Broadband, Mobile Phone, Credit Card, Plumbing, etc.

They click "Analyse & Submit".

### Step 2: The System Analyses the Complaint

Behind the scenes, three separate processes run on the complaint text:

1. **Classification** - The system reads the complaint and decides what category it belongs to. For example, if the text mentions "broadband" and "BT", it classifies it as "Telecoms". This is done by a neural network that has been trained on thousands of real complaints.

2. **Sentiment Analysis** - The system determines how the complaint sounds emotionally. It looks for negative words ("terrible", "disgusting", "unacceptable"), positive words ("pleased", "satisfied"), and urgency indicators ("immediately", "dangerous", "legal action"). It produces a score from -1 (very negative) to +1 (very positive) and an urgency level (low, medium, high, or critical).

3. **Named Entity Recognition (NER)** - The system scans the text to extract specific details: the company name, the product being complained about, how long the issue has been going on, and any monetary amounts mentioned. For example, from "BT hasn't fixed my broadband for 3 days", it extracts: company = "BT", product = "broadband", timeframe = "3 days".

### Step 3: The User Sees Results

After analysis, the user is taken to a results page showing:

- The predicted **category** with a confidence percentage (e.g., "Telecoms - 92% confidence")
- The **sentiment** label and score (e.g., "Negative - Score: -0.7")
- The **urgency** level (e.g., "High")
- The extracted **entities** (company, product, timeframe)
- A **recommended strategy** for how to complain effectively (e.g., "Ofcom-Referenced Service Complaint - 68% success rate")

### Step 4: The User Generates a Letter

The user clicks "Generate Complaint Letter". The system creates a formal PDF letter that includes:

- The user's name and the date
- The company's name
- A subject line
- A professionally written letter body that references relevant regulations (e.g., Ofcom for telecoms, Consumer Rights Act for retail)
- Specific numbered requests (e.g., "1. An immediate resolution to this issue")
- A formal closing

The letter is saved to the system and downloaded to the user's computer.

### Step 5 (Optional): Similar Style

If the user has another complaint of a similar nature, they can click "Similar to this style", paste a new complaint, and the system will generate a new letter using the same writing style and template as the previous one.

---

## 3. System Architecture

The system is built using a layered architecture with four main components:

```
User's Browser
      |
      v
[Django Web Application]  <-- Handles all web pages, forms, user accounts
      |
      +--> [ML Pipeline]  <-- Classifies complaints, analyses sentiment, extracts entities
      |
      +--> [Data Mining Engine]  <-- Finds patterns, clusters similar complaints
      |
      +--> [Letter Generator]  <-- Matches example letters, creates PDFs
      |
      v
[SQLite Database]  <-- Stores all data: users, complaints, training data, analysis results
```

### How requests flow through the system:

1. The user's browser sends a request to the Django web server
2. Django checks if the user is logged in (authentication)
3. Django processes the request through the appropriate view function
4. If the request involves a complaint, the ML pipeline runs
5. Results are saved to the database
6. Django renders an HTML page with the results and sends it back to the browser
7. The browser displays the page to the user

### The REST API:

In addition to regular web pages, the system also provides a REST API (Application Programming Interface). This means other programs or apps could interact with the system without using a web browser. The API provides endpoints for:

- Submitting complaints and receiving analysis results as JSON data
- Listing complaint categories
- Retrieving dashboard statistics

---

## 4. The Web Application (Web Development Module)

### Framework: Django

Django is a Python web framework that follows the Model-View-Template (MVT) pattern:

- **Models** define the structure of the database (what data is stored and how)
- **Views** contain the logic (what happens when a user visits a page)
- **Templates** define the appearance (the HTML that the user sees)

### The Apps

The project is divided into four Django "apps", each handling a different part of the system:

#### accounts (User Authentication)
Handles user registration, login, logout, and profiles. When a user registers, Django automatically hashes their password (converts it to an unreadable format) before storing it in the database. This means even if someone accessed the database, they could not read the passwords.

**Key files:**
- `accounts/models.py` - Defines a UserProfile that extends Django's built-in User model
- `accounts/views.py` - Handles registration (creating new accounts) and profile viewing
- `accounts/forms.py` - Defines the registration and login forms with validation
- `accounts/templates/` - The HTML pages for login, register, and profile

#### complaints (Core Functionality)
The main app that handles everything related to complaints: submission, analysis, history, letter generation, training, and the data collected page.

**Key files:**
- `complaints/models.py` - Defines the database structure for complaints, categories, strategies, and example letters
- `complaints/views.py` - Contains all the page logic (submit, detail, history, delete, train, generate letter, similar style, search companies)
- `complaints/forms.py` - Defines the complaint submission form and the training form, including the shared product/service dropdown
- `complaints/utils.py` - Contains the PDF letter generation logic
- `complaints/serializers.py` - Converts database objects to JSON for the REST API
- `complaints/api_views.py` - Handles API requests
- `complaints/templates/` - All the HTML pages

#### ml (Machine Learning)
Contains the neural network models, sentiment analyser, and entity extractor. This app does not have its own web pages - it provides functions that the complaints app calls.

**Key files:**
- `ml/classifier.py` - The LSTM and MLP neural network models
- `ml/sentiment.py` - The sentiment analysis system
- `ml/ner.py` - The named entity recognition system
- `ml/predictor.py` - The unified interface that runs all three systems together
- `ml/management/commands/train_models.py` - The training script
- `ml/management/commands/load_data.py` - The CFPB data loading script

#### mining (Data Mining)
Contains the pattern analysis, clustering, and association rule mining. Powers the analytics dashboard.

**Key files:**
- `mining/analysis.py` - Calculates distributions, trends, and statistics
- `mining/clustering.py` - Groups similar complaints using KMeans
- `mining/association.py` - Finds association rules using the Apriori algorithm
- `mining/views.py` - Renders the dashboard and provides data to Chart.js

### Frontend

The user interface is built with:

- **Bootstrap 5** - A CSS framework that provides pre-built components (buttons, cards, navigation bars, forms) for a professional, responsive design
- **Chart.js** - A JavaScript library that creates interactive charts (pie charts, bar charts, line graphs) for the analytics dashboard
- **Bootstrap Icons** - Icon set used throughout the interface

All pages extend a base template (`templates/base.html`) that provides the navigation bar, footer, and shared CSS/JavaScript.

### REST API

Built with Django REST Framework (DRF), the API provides:

- `GET /api/complaints/` - List the logged-in user's complaints
- `POST /api/complaints/` - Submit and analyse a new complaint
- `GET /api/complaints/{id}/` - Get details of a specific complaint
- `GET /api/categories/` - List all complaint categories
- `GET /api/dashboard/` - Get dashboard statistics

---

## 5. The Machine Learning Pipeline (Neural Networks Module)

When a complaint is submitted, three ML systems run in sequence. Here is how each one works:

### 5.1 Complaint Classification

**Purpose:** Determine what category a complaint belongs to (e.g., Telecoms, Retail, Property).

**How it works:**

The system has two classifiers: an LSTM (Long Short-Term Memory) neural network and an MLP (Multi-Layer Perceptron) neural network. Both are trained on the same data, and the system uses whichever performs better.

#### The LSTM Classifier

LSTM is a type of Recurrent Neural Network (RNN) designed to understand sequences of words. It processes a complaint one word at a time and remembers important context from earlier words. This makes it good at understanding text because the meaning of words depends on what came before them.

**Architecture:**

```
Input: "My broadband has been down for 3 days"
   |
   v
[Embedding Layer] - Converts each word into a numerical vector (a list of 128 numbers
                    that captures the word's meaning). Similar words get similar vectors.
   |
   v
[Bidirectional LSTM] - Reads the text both forwards and backwards. This means it
                       understands context from both directions. Uses 2 layers with
                       256 hidden units each. "Bidirectional" means one LSTM reads
                       left-to-right and another reads right-to-left.
   |
   v
[Dropout Layer] - Randomly disables 30% of neurons during training to prevent
                  overfitting (where the model memorises training data instead of
                  learning general patterns).
   |
   v
[Fully Connected Layer] - Takes the LSTM's output and produces a score for each
                          category. The category with the highest score is the
                          prediction.
   |
   v
Output: Category = "Telecoms" (confidence: 92%)
```

#### The MLP Classifier

MLP is a simpler neural network that does not understand word order. Instead, it averages all the word vectors together and passes the result through several layers of neurons.

**Architecture:**

```
Input: "My broadband has been down for 3 days"
   |
   v
[Embedding Layer] - Same as LSTM: converts words to 128-dimensional vectors
   |
   v
[Average Pooling] - Averages all word vectors into a single vector. This loses
                    word order information but is computationally simpler.
   |
   v
[Fully Connected Layer 1] - 256 neurons with ReLU activation
   |
   v
[Fully Connected Layer 2] - 128 neurons with ReLU activation
   |
   v
[Fully Connected Layer 3] - Outputs a score per category
   |
   v
Output: Category = "Telecoms" (confidence: 78%)
```

#### Why both?

The project trains both models and compares their performance. This comparative analysis demonstrates understanding of different neural network architectures. The LSTM typically outperforms the MLP because it understands word order, which is important for text classification.

#### Fallback: Rule-Based Classification

When no trained model exists (before the user has run `python manage.py train_models`), the system uses a simpler keyword-based approach. It checks the complaint text for keywords associated with each category:

- If the text contains "broadband", "wifi", "BT" -> Telecoms
- If the text contains "refund", "delivery", "faulty" -> Retail
- If the text contains "pipe", "leak", "landlord" -> Property
- And so on

This keyword list also includes keywords from any example letters the user has added through the Train AI page, so the system automatically learns new categories.

### 5.2 Sentiment Analysis

**Purpose:** Determine how negative/positive the complaint sounds and how urgent it is.

**How it works:**

The sentiment analyser uses a keyword-scoring approach:

1. **Negative words** ("terrible", "disgusting", "unacceptable", "furious") score -1 each
2. **Positive words** ("pleased", "satisfied", "thank") score +1 each
3. **Intensifiers** ("very", "extremely", "absolutely") multiply the next word's score by 1.5
4. **Negators** ("not", "never", "no") flip the next word's score (positive becomes negative)
5. **Urgency words** ("immediately", "dangerous", "legal action", "ombudsman") increase the urgency level

The system combines these scores into:
- A **sentiment score** from -1.0 to +1.0
- A **sentiment label**: positive (> 0.1), negative (< -0.1), or neutral
- An **urgency level**: critical, high, medium, or low

Example:
- "My broadband has been down" -> negative words: "down" -> Score: -0.3, Urgency: medium
- "This is absolutely disgraceful and I demand immediate action" -> negative words: "disgraceful", intensifier: "absolutely", urgency words: "immediate", "demand" -> Score: -0.85, Urgency: critical

### 5.3 Named Entity Recognition (NER)

**Purpose:** Extract specific details from the complaint text: company name, product, timeframe, monetary values.

**How it works:**

The NER system uses two approaches combined:

1. **Regex patterns** (Regular Expressions) - These are text-matching rules:
   - Company names: Looks for known company names (BT, Sky, EE, Vodafone, British Gas, etc.) and words followed by "Ltd", "PLC", or "Inc"
   - Timeframes: Matches patterns like "3 days", "two weeks", "since January", "last month"
   - Monetary values: Matches patterns like "£50.00", "£1,200"
   - Products: Matches common product/service terms

2. **spaCy** (if installed) - A pre-trained NLP library that uses its own neural network to identify entities in text. It can find company names, locations, dates, and monetary values that the regex patterns might miss.

Example:
- Input: "BT hasn't fixed my broadband for 3 days and I've been charged £45"
- Output: company = "BT", product = "broadband", timeframe = "3 days", monetary = "£45"

---

## 6. The Data Mining Engine (Data Mining Module)

The data mining module analyses complaint data to find patterns, trends, and groupings. It powers the analytics dashboard.

### 6.1 Pattern Analysis

**What it does:** Calculates statistics across all complaints.

- **Category distribution** - How many complaints per category (e.g., 45% Telecoms, 30% Retail)
- **Sentiment distribution** - How many complaints are positive, neutral, or negative
- **Urgency distribution** - How many complaints at each urgency level
- **Monthly trends** - How complaint volumes change over time
- **Company statistics** - Which companies receive the most complaints and their average sentiment scores
- **Keyword analysis** - The most commonly used words across all complaints (excluding common words like "the", "and", "is")

These statistics are displayed on the dashboard as interactive Chart.js charts.

### 6.2 Association Rule Mining (Apriori Algorithm)

**What it does:** Finds relationships between different complaint attributes.

**How it works:**

Each complaint is converted into a "transaction" - a set of features like:
- category:Telecoms
- sentiment:negative
- urgency:high
- company:BT

The Apriori algorithm (from the mlxtend library) then looks for rules like:

- "If category is Telecoms AND sentiment is negative, THEN urgency is high (85% confidence)"
- "If company is BT AND issue is Service outage, THEN consumer disputed (72% confidence)"

These rules reveal which types of complaints tend to be more urgent, which companies tend to have which problems, and which complaint strategies work best for which situations.

**Key terms:**
- **Support** - How often the combination appears in the data (e.g., 5% of all complaints are Telecoms + negative)
- **Confidence** - How reliable the rule is (e.g., 85% of Telecoms + negative complaints are high urgency)

### 6.3 Clustering (KMeans)

**What it does:** Groups similar complaints together automatically, without being told what the groups should be.

**How it works:**

1. **TF-IDF Vectorisation** - Each complaint's text is converted into a numerical vector. TF-IDF (Term Frequency - Inverse Document Frequency) gives higher scores to words that are important in a specific complaint but rare across all complaints. For example, "broadband" would score high in a telecom complaint but low overall because it only appears in telecom complaints.

2. **KMeans Algorithm** - The algorithm places 5 random "centre points" in the vector space, then:
   - Assigns each complaint to the nearest centre point
   - Moves each centre point to the middle of its assigned complaints
   - Repeats until the centres stop moving

3. **Cluster Summaries** - For each cluster, the system reports:
   - The top keywords (what the cluster is about)
   - The average sentiment
   - The dominant category
   - The number of complaints in the cluster

### 6.4 Outlier Detection

**What it does:** Identifies unusual complaints that don't fit neatly into any cluster.

**How it works:** After clustering, the system measures each complaint's distance from its nearest cluster centre. Complaints in the top 5% of distances are flagged as outliers. These might be unusual complaint types, edge cases, or complaints that span multiple categories.

### 6.5 The Dashboard

All of this analysis is visualised on a web dashboard using Chart.js:

- **Doughnut chart** - Category distribution
- **Pie chart** - Sentiment distribution
- **Line chart** - Monthly complaint trends over time
- **Bar chart** - Urgency level distribution
- **Horizontal bar chart** - Top companies by complaint count
- **Keyword cloud** - Most common words, sized by frequency

The dashboard fetches data from an API endpoint (`/dashboard/api/data/`) using JavaScript, so it loads asynchronously without refreshing the page.

---

## 7. Security Implementation (Security Engineering Module)

### 7.1 Password Security

User passwords are never stored in plain text. Django uses the PBKDF2 algorithm with SHA-256 hashing:

1. The user types their password (e.g., "mypassword123")
2. Django generates a random "salt" (extra random data)
3. The password + salt are run through SHA-256 hashing 600,000 times
4. The result is a long string of characters that looks nothing like the original password
5. This hashed value is what gets stored in the database

Even if someone accessed the database, they could not reverse the hash to find the original password. When the user logs in, Django hashes what they typed and compares it to the stored hash.

Additionally, Django enforces password rules:
- Minimum 8 characters
- Cannot be too similar to the username
- Cannot be a commonly used password (e.g., "password123")
- Cannot be entirely numeric

### 7.2 Encryption of Personal Data

Complaint text may contain personal information (names, addresses, account numbers). The system encrypts sensitive data using the Fernet encryption scheme (from the `cryptography` library):

1. A secret encryption key is generated and stored in the environment variables (not in the code)
2. When personal data is saved, it is encrypted using this key
3. The encrypted data is stored as unreadable binary in the database
4. When the data needs to be displayed, it is decrypted using the same key

Fernet uses AES-128-CBC encryption, which is the same standard used by banks and governments.

### 7.3 CSRF Protection

Cross-Site Request Forgery (CSRF) is an attack where a malicious website tricks a user's browser into making unwanted requests to your site. Django prevents this by:

1. Generating a unique random token for each user session
2. Including this token in every form on the website (as a hidden field: `{% csrf_token %}`)
3. When a form is submitted, Django checks that the token matches
4. If the token is missing or wrong, the request is rejected

This means a malicious website cannot submit forms on behalf of the user because it does not have the correct token.

### 7.4 XSS Prevention (Cross-Site Scripting)

XSS attacks involve injecting malicious JavaScript into web pages. Django prevents this by:

- **Auto-escaping** all template variables. If a user types `<script>alert('hacked')</script>` in their complaint, Django converts the `<` and `>` characters to `&lt;` and `&gt;`, so the browser displays the text instead of executing it as code.
- Setting the `X-XSS-Protection` header, which tells browsers to block pages that appear to contain XSS attacks.
- Setting `Content-Type-Nosniff` header, which prevents browsers from trying to guess the content type of responses.

### 7.5 SQL Injection Prevention

SQL injection is an attack where malicious SQL code is inserted into form inputs to manipulate the database. Django prevents this by using an ORM (Object-Relational Mapper):

- Instead of writing raw SQL queries like `SELECT * FROM complaints WHERE id = '` + user_input + `'`, Django uses Python objects: `Complaint.objects.get(id=user_input)`
- The ORM automatically parameterises all queries, meaning user input is always treated as data, never as SQL code
- Even if a user types `'; DROP TABLE complaints; --` in a form field, it would be treated as a literal string, not as a SQL command

### 7.6 Session Security

- Sessions expire after 1 hour of inactivity (`SESSION_COOKIE_AGE = 3600`)
- Sessions are destroyed when the browser is closed (`SESSION_EXPIRE_AT_BROWSER_CLOSE = True`)
- Session cookies are marked as HttpOnly, which prevents JavaScript from accessing them
- In production, cookies are marked as Secure (only sent over HTTPS)

### 7.7 Clickjacking Protection

The `X-Frame-Options: DENY` header prevents the website from being loaded inside an iframe on another website. This protects against clickjacking attacks where a malicious site overlays invisible buttons over the legitimate site.

### 7.8 GDPR Considerations

Since complaints contain personal data:
- Users can only view their own complaints (enforced in every view)
- Users can delete their complaints (and the associated letter files are deleted too)
- Personal data is encrypted at rest
- The system uses session timeouts to protect unattended computers

---

## 8. The Training System

The system can be trained in two ways:

### 8.1 CFPB Data (Bulk Training)

The Consumer Financial Protection Bureau (CFPB) provides a public database of over 4 million real consumer complaints. The system:

1. Downloads the CSV file (8GB)
2. Parses each row, extracting: product category, company name, complaint narrative, company response, and whether the response was timely
3. Saves them as `CFPBComplaint` records in the database
4. Uses the complaint narrative as training text and the product as the category label

Command: `python manage.py load_data`

### 8.2 Train AI Page (Individual Training)

Users can paste real complaint letters through the web interface. When they submit:

1. **Product/Service selection** - The user picks from the same dropdown used in the complaint form
2. **Company name** - The user types the company, or the system auto-detects it using NER
3. **Issue type detection** - The system scans for keywords to label the issue (e.g., "Service outage", "Billing dispute", "Faulty product")
4. **Keyword extraction** - The system removes common words (stopwords) and saves the top 15 most frequent words
5. **Template creation** - Company and product names in the letter are replaced with `{company}` and `{product}` placeholders, creating a reusable template
6. **Two records saved:**
   - An `ExampleLetter` record (for letter generation)
   - A `CFPBComplaint` record (for classifier training)

### 8.3 Model Training

When the user runs `python manage.py train_models`, the system:

1. Loads all `CFPBComplaint` records that have complaint text
2. Builds a vocabulary (the 10,000 most common words)
3. Splits data into training (70%), validation (15%), and test (15%) sets
4. Trains both the LSTM and MLP models for 20 epochs
5. Uses early stopping (saves the model with the best validation loss)
6. Prints a comparison table showing accuracy, precision, recall, and F1 score for both models
7. Saves the better model's weights, vocabulary, and category list

### 8.4 The "Similar to this style" Feature

When a user uses the "Similar to this style" button:

1. A new complaint is created and analysed
2. The system finds the example letter that matched the source complaint
3. A letter is generated using the same style
4. The new complaint text is saved as a CFPBComplaint (for classifier training)
5. The matched example letter style is saved as a new ExampleLetter (for letter generation)

This means every use of "Similar to this style" automatically adds to both training datasets.

---

## 9. The Letter Generation System

The letter generation follows a priority system:

### Priority 1: Example Letters (Learned from Training)

The system searches all `ExampleLetter` records and scores each one by:

- **Keyword overlap** (+3 points per matching keyword between the complaint and the example's saved keywords)
- **Word overlap** (+1 point per shared word between complaint text and letter body)
- **Issue type overlap** (+2 points per shared word in the issue type)
- **Company type match** (+2 points if the company type matches)
- **Category match** (+5 points if the category matches)

The highest-scoring example is selected (if its score is above 2, meaning there is meaningful overlap). The letter body is taken from this example, with `{company}`, `{product}`, `{timeframe}`, etc. replaced with the current complaint's details.

### Priority 2: Strategy Templates (Seeded Defaults)

If no example letter matches, the system falls back to the matched `ComplaintStrategy`. These are pre-written templates that reference relevant regulations:

- **Financial Services** - References FCA regulations and the Financial Ombudsman
- **Telecoms** - References Ofcom and Alternative Dispute Resolution
- **Utilities** - References Ofgem/Ofwat and the Energy Ombudsman
- **Retail** - References the Consumer Rights Act 2015 and Small Claims Court
- **Transport** - References Delay Repay schemes and Transport Focus

### Priority 3: Generic Fallback

If no strategy matches either, a basic template is used that describes the complaint and requests a response within 14 days.

### PDF Generation

The system uses ReportLab (a Python PDF library) to create the letter:

1. Creates an A4-sized document with 2.5cm margins
2. Adds the sender's name and date at the top
3. Adds the recipient (company name) - or skips this line if no company is known
4. Adds a bold subject line (e.g., "Subject: Formal Complaint - Telecoms")
5. Adds "Dear [Company]," or "Dear Sir/Madam,"
6. Adds the letter body
7. Adds "Yours faithfully," and the sender's name
8. Saves to the `media/letters/` directory and returns the PDF as a download

The system also strips any duplicate greetings or closings that might exist in the template (e.g., if the template already contains "Dear Sir/Madam" or "Kind regards").

---

## 10. Database Design

The system uses SQLite (a file-based database) with the following tables:

### User & Profile
- **auth_user** - Django's built-in user table (username, email, hashed password)
- **accounts_userprofile** - Extended user profile (date of birth, created date)

### Complaints
- **complaints_category** - Complaint categories (name, description, complaint count)
- **complaints_complaint** - User complaints with all analysis results:
  - `raw_text` - The original complaint text
  - `encrypted_personal_data` - Encrypted PII (binary)
  - `predicted_category` - Foreign key to Category
  - `category_confidence` - How confident the classifier is (0-1)
  - `sentiment_label` - positive/neutral/negative
  - `sentiment_score` - -1.0 to +1.0
  - `urgency_level` - low/medium/high/critical
  - `entities` - JSON field with all extracted entities
  - `company_name`, `product`, `timeframe` - Individual entity fields
  - `matched_strategy` - Foreign key to ComplaintStrategy
  - `letter_file` - Path to the generated PDF
  - `letter_generated` - Whether a letter has been generated

### Strategies & Templates
- **complaints_complaintstrategy** - Complaint strategies with letter templates, success rates
- **complaints_exampleletter** - User-submitted example letters with extracted keywords, issue types

### Training Data
- **complaints_cfpbcomplaint** - CFPB complaint records used for training the classifier

### Relationships

```
User ---(has many)---> Complaint
Category ---(has many)---> Complaint
Category ---(has many)---> ComplaintStrategy
Category ---(has many)---> ExampleLetter
ComplaintStrategy ---(matched to)---> Complaint
```

---

## 11. File Structure

```
Project/
|-- manage.py                    # Django's command-line tool
|-- requirements.txt             # Python package dependencies
|-- db.sqlite3                   # The database file
|
|-- complaint_assistant/         # Project configuration
|   |-- settings.py              # All settings (database, security, apps)
|   |-- urls.py                  # Root URL routing
|   |-- wsgi.py                  # Web server interface
|
|-- accounts/                    # User authentication app
|   |-- models.py                # UserProfile model
|   |-- views.py                 # Register, login, profile views
|   |-- forms.py                 # Registration and login forms
|   |-- urls.py                  # Account URL routes
|   |-- templates/accounts/      # Login, register, profile HTML pages
|
|-- complaints/                  # Core complaints app
|   |-- models.py                # Complaint, Category, Strategy, ExampleLetter models
|   |-- views.py                 # All complaint views (submit, detail, train, etc.)
|   |-- forms.py                 # Complaint and training forms
|   |-- utils.py                 # PDF letter generation
|   |-- serializers.py           # REST API data conversion
|   |-- api_views.py             # REST API endpoints
|   |-- urls.py                  # Complaint URL routes
|   |-- templates/complaints/    # All complaint HTML pages
|
|-- ml/                          # Machine learning module
|   |-- classifier.py            # LSTM and MLP neural networks
|   |-- sentiment.py             # Sentiment analysis
|   |-- ner.py                   # Named entity recognition
|   |-- predictor.py             # Unified prediction interface
|   |-- trained_models/          # Saved model weights and vocabulary
|   |-- management/commands/     # Training and data loading scripts
|
|-- mining/                      # Data mining module
|   |-- analysis.py              # Pattern analysis and statistics
|   |-- clustering.py            # KMeans clustering
|   |-- association.py           # Apriori association rules
|   |-- views.py                 # Dashboard views
|   |-- urls.py                  # Dashboard URL routes
|
|-- templates/                   # Shared templates
|   |-- base.html                # Base template (navbar, footer, CSS/JS)
|   |-- home.html                # Landing page
|
|-- static/                      # Static files
|   |-- css/style.css            # Custom styles
|   |-- js/dashboard.js          # Dashboard chart logic
|
|-- media/letters/               # Generated PDF letters
|-- data/                        # CFPB dataset and loading scripts
```

---

## 12. How to Set Up and Run

### Prerequisites
- Python 3.10 or later
- pip (Python package manager)

### Steps

```bash
# 1. Navigate to the project
cd D:/University/Dissitation/Project

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
venv/Scripts/activate        # Windows
source venv/bin/activate     # Mac/Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Download spaCy English model (for NER)
python -m spacy download en_core_web_sm

# 6. Create database tables
python manage.py makemigrations
python manage.py migrate

# 7. Seed default categories and strategies
python manage.py seed_data

# 8. Load CFPB training data (optional, takes a few minutes)
python manage.py load_data --file data/complaints.csv

# 9. Train the ML models (optional, takes a while)
python manage.py train_models

# 10. Create an admin account
python manage.py createsuperuser

# 11. Start the server
python manage.py runserver

# 12. Open in browser
# Home: http://127.0.0.1:8000/
# Admin: http://127.0.0.1:8000/admin/
```

---

## 13. Technologies Used

| Technology | Purpose | Module |
|---|---|---|
| **Python 3.14** | Programming language | All |
| **Django 5.2** | Web framework | Web Development |
| **Django REST Framework** | REST API | Web Development |
| **Bootstrap 5** | CSS framework for UI | Web Development |
| **Chart.js** | Interactive charts | Web Development / Data Mining |
| **PyTorch** | Neural network training | Neural Networks |
| **scikit-learn** | KMeans clustering, TF-IDF | Data Mining |
| **mlxtend** | Apriori association rules | Data Mining |
| **spaCy** | Named entity recognition | Neural Networks |
| **NLTK** | Natural language processing | Neural Networks |
| **pandas** | Data manipulation | Data Mining |
| **numpy** | Numerical computing | Neural Networks / Data Mining |
| **ReportLab** | PDF generation | Web Development |
| **cryptography** | Fernet encryption for PII | Security Engineering |
| **SQLite** | Database | All |
| **python-decouple** | Environment variables | Security Engineering |
