# 🧱 Bahata Bricks Kiln Management System

A modern **Brick Kiln ERP & Labour Ledger Management System** designed to digitize and simplify the day-to-day operations of a brick kiln.

The system provides tools for managing **brick production, labour records, Khata ledgers, payments, users, and printable reports** through a desktop application built with Python and PySide6.

---

## 📌 Overview

Managing a brick kiln traditionally involves maintaining production records, labour accounts, payments, and financial ledgers manually. This can make it difficult to track production accurately and maintain consistent records.

**Bahata Bricks Kiln Management System** provides a centralized digital solution for these operations.

The application is designed around the actual workflow of a brick kiln, including **piece-rate labour production**, **worker Khata accounts**, and **A4 printable reporting**.

---

## ✨ Features

### 🧱 Production Management

* Track brick production using a piece-rate system.
* Record production against workers/labourers.
* Maintain production history.
* Automatically calculate production-related amounts.
* Keep production records organized and searchable.

### 📒 Khata / Labour Ledger

* Maintain individual labour Khata accounts.
* Automatically record financial transactions.
* Track advances and payments.
* Maintain debit/credit records.
* Calculate outstanding balances.
* Reduce manual ledger calculations.

### 👥 User & Role Management

* Role-Based Access Control (RBAC).
* Separate access according to user roles.
* Protect administrative functionality from unauthorized access.

### 📊 Reports

* Generate structured reports.
* Support multi-page **A4 printing**.
* Generate printable production and ledger records.
* Organize information for record keeping and management.

### 🖥️ Desktop Application

* Modern graphical user interface.
* Built with **PySide6 / Qt**.
* Designed for Windows desktop usage.
* SQLite database for local data storage.

### 🗄️ Database

* SQLite-based local database.
* No separate database server required.
* Suitable for standalone/local deployment.
* Structured storage for production, labour, users, and financial records.

### 🧪 Testing

The repository includes a dedicated `tests` directory for application testing and validation.

---

## 🛠️ Technology Stack

| Technology                 | Purpose                      |
| -------------------------- | ---------------------------- |
| **Python**                 | Core application development |
| **PySide6**                | Desktop GUI / Qt interface   |
| **SQLite**                 | Local database               |
| **Qt**                     | UI framework                 |
| **PDF / Print Reporting**  | A4 report generation         |
| **PyTest / Testing Tools** | Application testing          |

---

## 📁 Project Structure

```text
Bahata-Bricks-Killn-Mangment-System-/
│
├── app/
│   ├── ...                 # Application source code
│   └── ...
│
├── tests/
│   ├── ...                 # Automated tests
│   └── ...
│
├── .gitignore
├── README.md
└── ...
```

> The exact internal structure may evolve as the application continues to be developed.

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Tanzeel175/Bahata-Bricks-Killn-Mangment-System-.git
```

Navigate into the project:

```bash
cd Bahata-Bricks-Killn-Mangment-System-
```

### 2. Create a Virtual Environment

It is recommended to use a Python virtual environment.

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

If the project contains a `requirements.txt` file:

```bash
pip install -r requirements.txt
```

If dependencies are managed through another configuration file, install them according to the project's current configuration.

### 4. Run the Application

Run the application's main entry point from the project directory.

```bash
python <main_file>.py
```

> Replace `<main_file>.py` with the application's actual entry-point file.

---

## 🔐 Role-Based Access Control

The system includes **RBAC (Role-Based Access Control)** to control access to different parts of the application.

This allows the system to distinguish between different types of users and restrict administrative operations where necessary.

---

## 🧮 Piece-Rate Production

A key feature of the system is **piece-rate production tracking**.

Instead of maintaining production records manually, the application can associate production quantities with labourers and use the configured piece-rate information to calculate the corresponding amounts.

This helps reduce calculation errors and makes labour accounting easier to manage.

---

## 📒 Khata System

The Khata system is designed to maintain a digital financial record for labourers.

Typical transactions can include:

```text
Opening Balance
      ↓
Production Earnings
      ↓
Advances / Deductions
      ↓
Payments
      ↓
Remaining Balance
```

This provides management with a clearer view of each labourer's account.

---

## 🖨️ Reporting

The application supports **multi-page A4 PDF/print reporting**, allowing records maintained inside the system to be converted into practical documents for:

* Production records
* Labour accounts
* Khata statements
* Financial records
* Management documentation

---

## 🗃️ Data Storage

The application uses **SQLite** for local data storage.

Advantages include:

* No external database server.
* Simple deployment.
* Local data persistence.
* Easy backup of the database file.
* Suitable for standalone desktop applications.

---

## 🔒 Data & Security

Because this application can contain business and financial records, deployment should follow appropriate security practices.

Recommended practices include:

* Use strong administrator credentials.
* Restrict access to the application computer.
* Regularly back up the SQLite database.
* Do not commit sensitive credentials or database files containing private business information to Git.
* Keep dependencies updated.

---

## 🧪 Testing

Tests are located in:

```text
tests/
```

Run the project's tests using the configured testing framework.

For a PyTest-based setup:

```bash
pytest
```

---

## 🔄 Development Status

**Status:** 🚧 Active Development

The system is being developed as a practical ERP solution for brick kiln operations. Features and internal architecture may change as development continues.

---

## 🎯 Project Goals

The main goals of the project are to:

* Digitize brick kiln operations.
* Reduce manual record keeping.
* Improve production tracking.
* Automate labour Khata calculations.
* Reduce accounting errors.
* Provide reliable printable reports.
* Improve access control.
* Keep business data organized in one system.

---

## 🤝 Contributing

Contributions, suggestions, and improvements are welcome.

### Contribution Workflow

1. Fork the repository.
2. Create a feature branch.

```bash
git checkout -b feature/your-feature
```

3. Make your changes.
4. Run the available tests.
5. Commit your changes.

```bash
git commit -m "Add: your feature"
```

6. Push the branch.

```bash
git push origin feature/your-feature
```

7. Open a Pull Request.

---

## 📜 License

No license has currently been specified for this repository.

If this project is intended to be open source, a license such as **MIT** can be added in a future release.

---

## 👨‍💻 Author

**Tanzeel Shahzad**

GitHub: [Tanzeel175](https://github.com/Tanzeel175)

---

## ⭐ Support the Project

If you find this project useful, consider giving the repository a ⭐ on GitHub.

Repository:

https://github.com/Tanzeel175/Bahata-Bricks-Killn-Mangment-System-

---

## 📌 Project Summary

**Bahata Bricks Kiln Management System** is a desktop-based ERP solution for brick kiln operations, combining **production management, labour Khata accounting, role-based access control, SQLite data storage, and A4 reporting** into a single application.

Built with:

**Python + PySide6 + SQLite**
