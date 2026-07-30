import json
import logging
import os

import azure.functions as func
import pyodbc

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# Helpers

def get_connection():
    """
    Connection string is read from an environment variable (App Setting in Azure,
    local.settings.json locally) -- never hardcoded in source, per Part C.
    """
    conn_str = os.environ["SQL_CONNECTION_STRING"]
    return pyodbc.connect(conn_str)


def row_to_employee(row):
    return {
        "EmployeeID": row.EmployeeID,
        "FirstName": row.FirstName,
        "LastName": row.LastName,
        "DepartmentID": row.DepartmentID,
        "Salary": float(row.Salary),
        "Bonus": float(row.Bonus) if row.Bonus is not None else None,
        "HireDate": row.HireDate.isoformat() if row.HireDate else None,
    }


def json_response(data, status_code=200):
    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=status_code,
        mimetype="application/json",
    )


def error_response(message, status_code=400):
    return json_response({"error": message}, status_code)


# Part A: CRUD

@app.route(route="employees", methods=["POST"])
def create_employee(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return error_response("Request body must be valid JSON", 400)

    required = ["FirstName", "LastName", "DepartmentID", "Salary", "HireDate"]
    missing = [f for f in required if f not in body]
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}", 400)

    bonus = body.get("Bonus")  # optional -- left as NULL if not provided

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Employee (FirstName, LastName, DepartmentID, Salary, Bonus, HireDate)
                OUTPUT INSERTED.EmployeeID
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                body["FirstName"], body["LastName"], body["DepartmentID"],
                body["Salary"], bonus, body["HireDate"],
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
        return json_response({"EmployeeID": new_id}, 201)
    except pyodbc.Error as e:
        logging.error(f"DB error creating employee: {e}")
        return error_response("Database error while creating employee", 500)


@app.route(route="employees/{id:int}", methods=["GET"])
def get_employee(req: func.HttpRequest) -> func.HttpResponse:
    emp_id = int(req.route_params.get("id"))
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Employee WHERE EmployeeID = ?", emp_id)
            row = cursor.fetchone()
        if row is None:
            return error_response("Employee not found", 404)
        return json_response(row_to_employee(row))
    except pyodbc.Error as e:
        logging.error(f"DB error fetching employee {emp_id}: {e}")
        return error_response("Database error", 500)


@app.route(route="employees", methods=["GET"])
def list_employees(req: func.HttpRequest) -> func.HttpResponse:
    department_id = req.params.get("departmentId")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if department_id:
                cursor.execute(
                    "SELECT * FROM Employee WHERE DepartmentID = ?", int(department_id)
                )
            else:
                cursor.execute("SELECT * FROM Employee")
            rows = cursor.fetchall()
        return json_response([row_to_employee(r) for r in rows])
    except (pyodbc.Error, ValueError) as e:
        logging.error(f"DB error listing employees: {e}")
        return error_response("Database error or invalid departmentId", 400)


@app.route(route="employees/{id:int}", methods=["PUT"])
def update_employee(req: func.HttpRequest) -> func.HttpResponse:
    emp_id = int(req.route_params.get("id"))
    try:
        body = req.get_json()
    except ValueError:
        return error_response("Request body must be valid JSON", 400)

    allowed_fields = ["FirstName", "LastName", "DepartmentID", "Salary", "Bonus", "HireDate"]
    updates = {k: v for k, v in body.items() if k in allowed_fields}
    if not updates:
        return error_response("No valid fields to update", 400)

    set_clause = ", ".join(f"{field} = ?" for field in updates)
    values = list(updates.values()) + [emp_id]

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE Employee SET {set_clause} WHERE EmployeeID = ?", *values)
            if cursor.rowcount == 0:
                return error_response("Employee not found", 404)
            conn.commit()
        return json_response({"message": "Employee updated"})
    except pyodbc.Error as e:
        logging.error(f"DB error updating employee {emp_id}: {e}")
        return error_response("Database error", 500)


@app.route(route="employees/{id:int}", methods=["DELETE"])
def delete_employee(req: func.HttpRequest) -> func.HttpResponse:
    emp_id = int(req.route_params.get("id"))
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Employee WHERE EmployeeID = ?", emp_id)
            if cursor.rowcount == 0:
                return error_response("Employee not found", 404)
            conn.commit()
        return json_response({"message": "Employee deleted"})
    except pyodbc.Error as e:
        logging.error(f"DB error deleting employee {emp_id}: {e}")
        return error_response("Database error", 500)


# Part B: Compensation reporting

@app.route(route="reports/total-bonus", methods=["GET"])
def total_bonus(req: func.HttpRequest) -> func.HttpResponse:
    """Total bonus paid company-wide, treating NULL bonuses as 0."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(ISNULL(Bonus, 0)) AS TotalBonus FROM Employee")
            row = cursor.fetchone()
        return json_response({"TotalBonus": float(row.TotalBonus or 0)})
    except pyodbc.Error as e:
        logging.error(f"DB error in total_bonus: {e}")
        return error_response("Database error", 500)


@app.route(route="reports/no-bonus", methods=["GET"])
def employees_without_bonus(req: func.HttpRequest) -> func.HttpResponse:
    """All employees who have never received a bonus."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Employee WHERE Bonus IS NULL")
            rows = cursor.fetchall()
        return json_response([row_to_employee(r) for r in rows])
    except pyodbc.Error as e:
        logging.error(f"DB error in employees_without_bonus: {e}")
        return error_response("Database error", 500)


@app.route(route="reports/bonus-percentage", methods=["GET"])
def bonus_percentage(req: func.HttpRequest) -> func.HttpResponse:
    """For each employee WITH a bonus, bonus as % of salary, rounded to 2 dp."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT EmployeeID, FirstName, LastName,
                       ROUND((Bonus / Salary) * 100, 2) AS BonusPercentage
                FROM Employee
                WHERE Bonus IS NOT NULL
                """
            )
            rows = cursor.fetchall()
        result = [
            {
                "EmployeeID": r.EmployeeID,
                "FirstName": r.FirstName,
                "LastName": r.LastName,
                "BonusPercentage": float(r.BonusPercentage),
            }
            for r in rows
        ]
        return json_response(result)
    except pyodbc.Error as e:
        logging.error(f"DB error in bonus_percentage: {e}")
        return error_response("Database error", 500)


@app.route(route="reports/departments-bonus-exceeds-avg-salary", methods=["GET"])
def departments_bonus_exceeds_avg_salary(req: func.HttpRequest) -> func.HttpResponse:
    """Departments where total bonus paid exceeds the department's average salary."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT d.DepartmentID, d.DepartmentName,
                       SUM(ISNULL(e.Bonus, 0)) AS TotalBonus,
                       AVG(e.Salary) AS AvgSalary
                FROM Department d
                JOIN Employee e ON e.DepartmentID = d.DepartmentID
                GROUP BY d.DepartmentID, d.DepartmentName
                HAVING SUM(ISNULL(e.Bonus, 0)) > AVG(e.Salary)
                """
            )
            rows = cursor.fetchall()
        result = [
            {
                "DepartmentID": r.DepartmentID,
                "DepartmentName": r.DepartmentName,
                "TotalBonus": float(r.TotalBonus),
                "AverageSalary": float(r.AvgSalary),
            }
            for r in rows
        ]
        return json_response(result)
    except pyodbc.Error as e:
        logging.error(f"DB error in departments_bonus_exceeds_avg_salary: {e}")
        return error_response("Database error", 500)


@app.route(route="reports/employees-ranked-by-bonus", methods=["GET"])
def employees_ranked_by_bonus(req: func.HttpRequest) -> func.HttpResponse:
    """Employees ranked by bonus amount; no-bonus employees ranked last, not excluded."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT EmployeeID, FirstName, LastName, Bonus
                FROM Employee
                ORDER BY CASE WHEN Bonus IS NULL THEN 1 ELSE 0 END, Bonus DESC
                """
            )
            rows = cursor.fetchall()
        result = [
            {
                "EmployeeID": r.EmployeeID,
                "FirstName": r.FirstName,
                "LastName": r.LastName,
                "Bonus": float(r.Bonus) if r.Bonus is not None else None,
            }
            for r in rows
        ]
        return json_response(result)
    except pyodbc.Error as e:
        logging.error(f"DB error in employees_ranked_by_bonus: {e}")
        return error_response("Database error", 500)


@app.route(route="reports/highest-compensation", methods=["GET"])
def highest_compensation(req: func.HttpRequest) -> func.HttpResponse:
    """
    The employee with the highest base salary, and separately, whether that
    same person also has the highest total compensation (salary + bonus).
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT TOP 1 EmployeeID, FirstName, LastName, Salary
                FROM Employee
                ORDER BY Salary DESC
                """
            )
            highest_salary_row = cursor.fetchone()

            cursor.execute(
                """
                SELECT TOP 1 EmployeeID, FirstName, LastName,
                       (Salary + ISNULL(Bonus, 0)) AS TotalComp
                FROM Employee
                ORDER BY TotalComp DESC
                """
            )
            highest_comp_row = cursor.fetchone()

        if highest_salary_row is None:
            return error_response("No employees found", 404)

        result = {
            "HighestSalaryEmployee": {
                "EmployeeID": highest_salary_row.EmployeeID,
                "FirstName": highest_salary_row.FirstName,
                "LastName": highest_salary_row.LastName,
                "Salary": float(highest_salary_row.Salary),
            },
            "SamePersonHasHighestTotalCompensation": (
                highest_salary_row.EmployeeID == highest_comp_row.EmployeeID
            ),
            "HighestTotalCompensationEmployee": {
                "EmployeeID": highest_comp_row.EmployeeID,
                "FirstName": highest_comp_row.FirstName,
                "LastName": highest_comp_row.LastName,
                "TotalCompensation": float(highest_comp_row.TotalComp),
            },
        }
        return json_response(result)
    except pyodbc.Error as e:
        logging.error(f"DB error in highest_compensation: {e}")
        return error_response("Database error", 500)


# Part C: default 5% bonus for employees who don't have one.
# Computed at READ time, not written to the table

@app.route(route="reports/effective-bonus", methods=["GET"])
def effective_bonus(req: func.HttpRequest) -> func.HttpResponse:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT EmployeeID, FirstName, LastName, Salary, Bonus,
                       CASE WHEN Bonus IS NULL THEN ROUND(Salary * 0.05, 2)
                            ELSE Bonus END AS EffectiveBonus
                FROM Employee
                """
            )
            rows = cursor.fetchall()
        result = [
            {
                "EmployeeID": r.EmployeeID,
                "FirstName": r.FirstName,
                "LastName": r.LastName,
                "Salary": float(r.Salary),
                "ActualBonus": float(r.Bonus) if r.Bonus is not None else None,
                "EffectiveBonus": float(r.EffectiveBonus),
            }
            for r in rows
        ]
        return json_response(result)
    except pyodbc.Error as e:
        logging.error(f"DB error in effective_bonus: {e}")
        return error_response("Database error", 500)
