# Employee Compensation Service

Azure Functions (Python, HTTP-triggered) backed by Azure SQL Database. All reads
and writes to the data go through this Functions layer — there is no direct
database access from clients.

## Architecture

```
Client --> Azure Function App (this code) --> Azure SQL Database
```

The SQL connection string is read from an environment variable
(`SQL_CONNECTION_STRING`) — an App Setting in Azure, or `local.settings.json`
locally. It is never hardcoded in source.

## Project structure

```
EmployeeCompensationService/
├── function_app.py       # all HTTP-triggered functions (CRUD + reporting)
├── host.json             # Functions host config
├── requirements.txt      # Python dependencies
├── local.settings.json   # local-only secrets (NOT committed, see .gitignore)
├── .gitignore
└── sql/
    ├── create_tables.sql
    └── seed_data.sql
```

---

## Part 1 — Create the Azure resources (Portal)

You said you're on Azure for Students — this all fits comfortably in the free
credit / free tier.

### 1.1 Create a Resource Group

1. Go to https://portal.azure.com
2. Search "Resource groups" → **+ Create**
3. Name: `rg-employee-comp` → pick a region close to you (e.g. Central India) → **Review + create** → **Create**

### 1.2 Create the Azure SQL Database

1. In the portal search bar, type **SQL databases** → **+ Create**
2. **Resource group**: `rg-employee-comp`
3. **Database name**: `EmployeeCompDb`
4. **Server**: click **Create new**
   - Server name: something globally unique, e.g. `employeecomp-sql-<yourname>`
   - Location: same region as your resource group
   - Authentication: **Use SQL authentication**
   - Set an admin login and a strong password — **write these down**, you'll need them for the connection string
5. **Compute + storage**: click **Configure database** → choose **Serverless**, and pick the smallest/free-eligible tier offered on your subscription (Azure for Students often shows a "Free" workload or the smallest General Purpose serverless tier — pick whichever is cheapest/free). Don't worry about getting this perfect; you can change it later.
6. **Networking** tab:
   - Connectivity method: **Public endpoint**
   - **Allow Azure services and resources to access this server** → **Yes** (your Function App needs this)
   - **Add current client IP address** → **Yes** (so you can run SQL scripts from your laptop)
7. **Review + create** → **Create**. This takes a few minutes.

### 1.3 Create the tables

1. Once deployed, go to your SQL database resource → **Query editor (preview)** in the left menu
2. Sign in with the admin login/password you set
3. Paste in the contents of `sql/create_tables.sql` → **Run**
4. Paste in the contents of `sql/seed_data.sql` → **Run**

(If the browser Query editor gives you trouble, install **Azure Data Studio** or **SSMS** free and connect with the same server name/login instead.)

### 1.4 Get the connection string

1. On the SQL database resource → left menu → **Connection strings**
2. Copy the **ODBC** connection string, it looks like:
   ```
   Driver={ODBC Driver 18 for SQL Server};Server=tcp=employeecomp-sql-yourname.database.windows.net,1433;Database=EmployeeCompDb;Uid={your_username};Pwd={your_password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
   ```
3. Replace `{your_username}` and `{your_password}` with your actual admin login/password. Keep this handy for the next section.

### 1.5 Create the Function App (do this now or after local testing — your choice)

1. Search **Function App** → **+ Create**
2. Resource group: `rg-employee-comp`
3. Function App name: something unique, e.g. `employeecomp-func-<yourname>`
4. **Runtime stack**: Python, version 3.10 or 3.11
5. **Region**: same as your other resources
6. **Hosting**: Consumption (Serverless) plan — this is the free-tier-friendly option
7. **Review + create** → **Create**

---

## Part 2 — Local development setup

### 2.1 Install prerequisites (Windows)

1. **Python 3.10 or 3.11** — https://www.python.org/downloads/ (check "Add to PATH" during install)
2. **Azure Functions Core Tools** — easiest via npm:
   ```
   npm install -g azure-functions-core-tools@4 --unsafe-perm true
   ```
   (or use the MSI installer from Microsoft Learn if you don't have Node/npm)
3. **ODBC Driver 18 for SQL Server** — download and run the MSI from Microsoft:
   https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
   (`pyodbc` needs this installed on your machine to talk to SQL Server)
4. In VS Code, confirm the **Azure Functions** and **Azure Account** extensions are enabled (you said you already have these).

### 2.2 Set up the project

1. Copy this whole `EmployeeCompensationService` folder to your machine, open it in VS Code
2. Open a terminal in that folder and create a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Open `local.settings.json` and replace the placeholder `SQL_CONNECTION_STRING`
   value with your real connection string from step 1.4.

### 2.3 Run it locally

```
func start
```

You should see all the routes listed in the terminal, e.g.:
```
http://localhost:7071/api/employees                 [GET,POST]
http://localhost:7071/api/employees/{id}             [GET,PUT,DELETE]
http://localhost:7071/api/reports/total-bonus        [GET]
...
```

### 2.4 Test it

Using `curl`, PowerShell, or Postman:

```
# Create an employee
curl -X POST http://localhost:7071/api/employees ^
  -H "Content-Type: application/json" ^
  -d "{\"FirstName\":\"Test\",\"LastName\":\"User\",\"DepartmentID\":1,\"Salary\":500000,\"HireDate\":\"2024-01-01\"}"

# Get all employees
curl http://localhost:7071/api/employees

# Get employees in department 1
curl http://localhost:7071/api/employees?departmentId=1

# Update bonus
curl -X PUT http://localhost:7071/api/employees/1 ^
  -H "Content-Type: application/json" ^
  -d "{\"Bonus\":50000}"

# Delete
curl -X DELETE http://localhost:7071/api/employees/1

# Reports
curl http://localhost:7071/api/reports/total-bonus
curl http://localhost:7071/api/reports/no-bonus
curl http://localhost:7071/api/reports/bonus-percentage
curl http://localhost:7071/api/reports/departments-bonus-exceeds-avg-salary
curl http://localhost:7071/api/reports/employees-ranked-by-bonus
curl http://localhost:7071/api/reports/highest-compensation
curl http://localhost:7071/api/reports/effective-bonus
```

---

## Part 3 — Deploy to Azure

Easiest path with the VS Code Azure extension you already have:

1. Click the **Azure** icon in the VS Code sidebar → sign in if needed
2. Under **Workspace**, right-click your Function project folder → **Deploy to Function App**
3. Choose the Function App you created in step 1.5 (or let it create a new one)
4. Once deployed, go to the Function App resource in the portal → **Configuration** → **Application settings** → **+ New application setting**
   - Name: `SQL_CONNECTION_STRING`
   - Value: your real connection string (same as local.settings.json)
   - **Save**
5. Your live endpoints will be at:
   ```
   https://<your-function-app-name>.azurewebsites.net/api/employees
   ```
   (Since `http_auth_level=FUNCTION` is set, you'll need to pass the function key as `?code=<key>` in the URL, or as the `x-functions-key` header — find keys under the Function App → **App keys**.)

---

## Endpoints reference

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/employees` | Create employee (Bonus optional) |
| GET | `/api/employees/{id}` | Get one employee |
| GET | `/api/employees?departmentId=` | List employees, optional department filter |
| PUT | `/api/employees/{id}` | Update employee (partial body allowed) |
| DELETE | `/api/employees/{id}` | Delete employee |
| GET | `/api/reports/total-bonus` | Total bonus paid company-wide (NULL = 0) |
| GET | `/api/reports/no-bonus` | Employees who never received a bonus |
| GET | `/api/reports/bonus-percentage` | Bonus as % of salary, per employee with a bonus |
| GET | `/api/reports/departments-bonus-exceeds-avg-salary` | Departments where total bonus > avg salary |
| GET | `/api/reports/employees-ranked-by-bonus` | Employees ranked by bonus, no-bonus employees ranked last |
| GET | `/api/reports/highest-compensation` | Highest base salary, and whether same person has highest total comp |
| GET | `/api/reports/effective-bonus` | (Optional, Part C) Default 5% bonus applied for employees without one |

---

## Design notes (Part C)

- **Secrets**: the connection string lives only in `local.settings.json` (git-ignored)
  locally, and in Function App **Application settings** in Azure — never in source.
- **Error handling**: every endpoint validates input and wraps DB calls in
  try/except, returning `400` for bad input, `404` for missing records, and
  `500` for unexpected DB errors, rather than leaking a raw exception/stack trace.
- **Default 5% bonus (optional requirement)**: I chose to compute this at
  **read time** (`/api/reports/effective-bonus`) rather than writing it into
  the `Bonus` column. Reasoning:
  - It keeps `Bonus IS NULL` meaningful as "no bonus has actually been
    awarded" — useful for the other reports (`no-bonus`, `ranked-by-bonus`).
  - It avoids a bulk write/migration and keeps the default logic in one place,
    so if the default percentage ever changes, no historical data needs to be
    rewritten.
  - The trade-off: every read recomputes it, which is trivial at this scale
    but would need a materialized/cached column at very large scale.

## What to submit (per the assignment)

1. This repository (source code) — zip it or push to a Git repo
2. This README
3. `sql/create_tables.sql` and `sql/seed_data.sql`
