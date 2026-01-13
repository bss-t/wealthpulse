# Expense Management System

A comprehensive web-based expense tracking and budget management system built with Python Flask.

## Features

- **💰 Expense Tracking**: Add, edit, and delete expenses with categories
- **📊 Budget Management**: Set monthly budgets and track spending
- **📈 Dashboard**: Visual analytics with charts and summaries
- **🏷️ Categories**: Organize expenses with custom categories
- **💳 Multiple Payment Methods**: Track cash, card, and digital payments
- **🧾 Receipt Upload**: Attach receipt images to expenses
- **📱 Responsive Design**: Mobile-friendly interface
- **📋 Reports**: Generate detailed expense reports
- **🔍 Search & Filter**: Advanced filtering and search capabilities
- **💱 Multi-Currency**: Support for different currencies

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database**:
   ```bash
   python run.py init-db
   ```

3. **Run the Application**:
   ```bash
   python run.py
   ```

4. **Access the Application**:
   - Open your browser to `http://localhost:5000`
   - Default login: user@expense.com / password123

## Project Structure

```
expense_manager/
├── app/
│   ├── models.py          # Database models
│   ├── routes.py          # Application routes
│   ├── forms.py           # WTF forms
│   ├── __init__.py        # App factory
│   ├── auth/              # Authentication blueprint
│   ├── main/              # Main application blueprint
│   ├── expenses/          # Expense management blueprint
│   ├── templates/         # HTML templates
│   └── static/           # CSS, JS, uploads
├── config.py             # Configuration
├── run.py               # Application entry point
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Default Categories

- 🍔 Food & Dining
- 🚗 Transportation
- 🏠 Housing & Utilities
- 🛍️ Shopping & Entertainment
- 💊 Healthcare
- 📚 Education
- 💼 Business
- 🎯 Other

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite (easily changeable to PostgreSQL/MySQL)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **File Upload**: PIL/Pillow for image processing