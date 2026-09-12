# 👁️ Drishti AI Sql Analyser

An AI-powered application that converts natural-language questions about NYC Yellow Taxi trips into SQL queries, executes them, and presents results with interactive visualizations and business-friendly explanations.

Built with Python, PostgreSQL, Streamlit, and OpenAI.

---

## 🎯 What It Does

**You ask a question in plain English** → The AI:
1. Understands your question
2. Inspects the database schema
3. Generates a safe SQL query
4. Validates the SQL for safety & correctness
5. Executes the query
6. Validates the results
7. Retries if something went wrong (up to 3 times)
8. Picks the best visualization (bar chart, line chart, etc.)
9. Writes a business-friendly explanation
10. Shows everything in a clean dashboard

---

## 📊 Dataset

**NYC Yellow Taxi Trip Records — January 2026**
- **3.7 million** trip records
- **20 columns** including pickup/dropoff times, locations, fares, tips, distances
- **265 taxi zones** with borough and neighborhood names

---

## 🛠️ Prerequisites

Before starting, you need to install these tools on your computer:

### 1. Python (3.10 or newer)

Check if Python is installed:
```bash
python --version
```

If not installed, download from: https://www.python.org/downloads/

### 2. PostgreSQL (14 or newer)

Download and install from: https://www.postgresql.org/downloads/windows/

During installation:
- **Remember the password** you set for the `postgres` user
- Keep the default port: **5432**
- Leave everything else as default

After installation, verify it's running:
```bash
psql -U postgres -c "SELECT version();"
```

### 3. Gemini API Key

1. Go to https://platform.openai.com/api-keys
2. Create an account (or sign in)
3. Click **"Create new secret key"**
4. Copy the key (starts with `sk-`)
5. You'll need this key in the setup steps below

> **Cost:** This app uses `gemini-3.1-flash-lite` by default, which is a free agent by google.

---

## 🚀 Setup Instructions (Step by Step)

### Step 1: Open a Terminal

Open **PowerShell** or **Command Prompt** on Windows.

### Step 2: Navigate to the Project Folder

```powershell
cd "d:\sql analyst"
```

### Step 3: Install Python Dependencies

```powershell
pip install -r requirements.txt
```

This installs: Streamlit, Pandas, PyArrow, Plotly, OpenAI, psycopg2, sqlparse, python-dotenv

### Step 4: Create the `.env` File

Copy the example and edit it:
```powershell
copy .env.example .env
```

Open `.env` in a text editor and fill in your values:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=taxi_analytics
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRESQL_PASSWORD_HERE
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY_HERE
OPENAI_MODEL=gpt-4o-mini
```

### Step 5: Create the PostgreSQL Database

Open a terminal and run:
```powershell
psql -U postgres -c "CREATE DATABASE taxi_analytics;"
```

If prompted for a password, enter the password you set during PostgreSQL installation.

### Step 6: Create the Database Tables

```powershell
psql -U postgres -d taxi_analytics -f sql/schema.sql
```

### Step 7: Load the Data

This loads 3.7 million taxi trips and 265 taxi zones into the database.
**This takes 10-20 minutes** depending on your computer.

```powershell
python -m app.database.loader
```

You'll see progress updates like:
```
Step 3: Loading trip data...
  Inserted     50,000 / 3,724,889 rows (1.3%)
  Inserted    100,000 / 3,724,889 rows (2.7%)
  ...
```

### Step 8: Run the Application

```powershell
streamlit run app/main.py
```

The app will open in your browser at **http://localhost:8501**

---

## 💡 Example Questions

Try asking these questions in the app:

| Question | Expected Visualization |
|----------|----------------------|
| "Which five pickup zones had the most taxi trips?" | Bar chart |
| "What is the average fare amount by payment type?" | Bar chart |
| "Show the busiest hours of the day for taxi pickups" | Line/Bar chart |
| "What is the average tip percentage by borough?" | Bar chart |
| "How many total trips were there in January 2026?" | KPI |
| "What were the total trips per day in January 2026?" | Line chart |
| "What is the distribution of trip distances?" | Histogram |
| "Which pickup-dropoff zone pair is most common?" | Table |

---

## 🔒 Security

The application enforces strict security:

- **Read-only queries only** — DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, GRANT, REVOKE are all blocked
- **SQL injection prevention** — Multiple statements and semicolons in queries are rejected
- **Query timeouts** — 30-second timeout prevents runaway queries
- **Row limits** — Maximum 1,000 rows returned per query
- **Read-only transactions** — Database connection uses SET TRANSACTION READ ONLY
- **No arbitrary code execution** — The LLM returns structured metadata, not executable code

---

## 📁 Project Structure

```
sql-analyst/
├── app/
│   ├── main.py                 # Streamlit entry point
│   ├── config.py               # All settings and configuration
│   ├── agent/
│   │   ├── orchestrator.py     # Main pipeline coordinator
│   │   ├── schema_retriever.py # Gets DB schema for the LLM
│   │   ├── sql_generator.py    # Converts questions → SQL
│   │   ├── sql_validator.py    # Validates SQL safety
│   │   ├── result_validator.py # Validates query results
│   │   ├── visualizer.py       # Selects & creates charts
│   │   └── explainer.py        # Generates explanations
│   ├── database/
│   │   ├── connection.py       # PostgreSQL connection
│   │   ├── loader.py           # Loads Parquet → PostgreSQL
│   │   ├── schema.py           # Schema utilities
│   │   └── executor.py         # Executes SQL queries
│   └── ui/
│       └── dashboard.py        # Streamlit UI components
├── data/
│   ├── yellow_tripdata_2026-01.parquet
│   └── taxi_zones.csv
├── sql/
│   └── schema.sql              # Database table definitions
├── tests/
│   └── test_validation.py      # Automated tests
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🧪 Running Tests

Tests run without a database or API key:

```powershell
pip install pytest
python -m pytest tests/test_validation.py -v
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `psycopg2.OperationalError: connection refused` | Make sure PostgreSQL is running. On Windows, check Services app. |
| `OPENAI_API_KEY not set` | Make sure `.env` file exists and has your API key. |
| `relation "yellow_taxi_trips" does not exist` | Run `psql -U postgres -d taxi_analytics -f sql/schema.sql` |
| `table has 0 rows` | Run `python -m app.database.loader` to load the data |
| `python not found` | Use the full path: `C:\Users\YOU\AppData\Local\Python\...\python.exe` |

---

## 📝 License

This project is for educational/hackathon purposes.
Dataset: [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
