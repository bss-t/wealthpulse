# WealthPulse — Expense Manager

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/) [![Flask](https://img.shields.io/badge/flask-2.3.3-orange)](https://palletsprojects.com/p/flask/)

WealthPulse is an open-source **expense manager** and **personal finance** web application built with **Python Flask** and PostgreSQL. It helps you track expenses, attach receipts, set budgets, and visualize spending—ideal for individuals and small businesses.

Key topics: `expense manager`, `personal finance`, `budgeting`, `expense tracker`, `flask`, `python`.

---

## Quick demo

![WealthPulse screenshot](.github/social_preview.svg)

---

## Features

- Add, edit, and delete expenses (title, description, amount, date, category)
- Receipt upload and viewing (images, PDF)
- Auto-category suggestions using ML (TF-IDF + Naive Bayes)
- Budgets, summaries, and charts (monthly/weekly totals)
- Search, filter, and duplicate detection
- Responsive UI (Bootstrap 5) and keyboard shortcuts
- Multi-user support with secure authentication (Flask-Login)

## Installation (local development)

1. Clone the repo:
```bash
git clone https://github.com/bss-t/wealthpulse.git
cd wealthpulse
```

2. Create virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Configure environment variables (create `.env`):
```
FLASK_ENV=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/expense_manager
SECRET_KEY=replace-with-secret
```

4. Initialize DB and run app:
```bash
flask db upgrade  # or python run.py init-db
flask run
```

Open http://localhost:5000

---

## Documentation
See the docs: `https://<your-gh-username>.github.io/wealthpulse/` (will be enabled via GitHub Pages). Docs live under `/docs` in this repo.

## Contributing
Contributions welcome! Please read `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` (coming soon).

## License
MIT

---

If you'd like, I can also enable GitHub Pages, add repo topics, and create a `v0.1` release to make the project more discoverable.