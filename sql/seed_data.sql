-- Employee Compensation Service - Sample seed data
-- Run this AFTER create_tables.sql

INSERT INTO Department (DepartmentName, Location) VALUES
('Engineering', 'Pune'),
('Sales',       'Mumbai'),
('HR',          'Pune'),
('Finance',     'Bengaluru');
GO

-- DepartmentID: 1 = Engineering, 2 = Sales, 3 = HR, 4 = Finance
INSERT INTO Employee (FirstName, LastName, DepartmentID, Salary, Bonus, HireDate) VALUES
('Aditi',  'Sharma',  1, 1200000.00, 120000.00, '2021-03-15'),
('Rohan',  'Verma',   1,  950000.00,        NULL, '2022-07-01'),
('Kabir',  'Mehta',   1, 1500000.00, 200000.00, '2019-11-20'),
('Sneha',  'Iyer',    2,  700000.00,   35000.00, '2020-01-10'),
('Arjun',  'Nair',    2,  650000.00,        NULL, '2023-05-05'),
('Priya',  'Rao',     3,  600000.00,   15000.00, '2018-09-12'),
('Vikram', 'Singh',   3,  580000.00,        NULL, '2022-02-28'),
('Neha',   'Kapoor',  4,  900000.00,  100000.00, '2021-06-18'),
('Aman',   'Gupta',   4,  850000.00,        NULL, '2020-12-01');
GO
