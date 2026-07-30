-- Employee Compensation Service - Table creation script
-- Run this in the Query Editor of your Azure SQL Database (or via SSMS / Azure Data Studio)

CREATE TABLE Department (
    DepartmentID   INT IDENTITY(1,1) PRIMARY KEY,
    DepartmentName VARCHAR(100) NOT NULL,
    Location       VARCHAR(100) NULL
);
GO

CREATE TABLE Employee (
    EmployeeID   INT IDENTITY(1,1) PRIMARY KEY,
    FirstName    VARCHAR(50)   NOT NULL,
    LastName     VARCHAR(50)   NOT NULL,
    DepartmentID INT           NOT NULL,
    Salary       DECIMAL(12,2) NOT NULL,
    Bonus        DECIMAL(12,2) NULL,      -- NULL = employee has not received a bonus
    HireDate     DATE          NOT NULL,
    CONSTRAINT FK_Employee_Department FOREIGN KEY (DepartmentID)
        REFERENCES Department(DepartmentID)
);
GO
