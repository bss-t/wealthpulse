"""
Chat Assistant for Expense Manager
Provides AI-powered chat interface for managing expenses, investments, and financial data
"""

from datetime import datetime, date
from sqlalchemy import func
from app.models import User, Expense, Category, Investment, InvestmentType, PaymentMethod, Budget
from app import db
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import io
import base64
from collections import defaultdict

class ExpenseManagerAssistant:
    """AI Assistant with access to WealthPulse functionality"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.user = User.query.get(user_id)
        if not self.user:
            raise ValueError(f"User {user_id} not found")
    
    def get_available_functions(self):
        """Return list of available functions for the AI"""
        return {
            "add_expense": self.add_expense,
            "list_expenses": self.list_expenses,
            "get_expense_summary": self.get_expense_summary,
            "list_categories": self.list_categories,
            "add_category": self.add_category,
            "add_investment": self.add_investment,
            "list_investments": self.list_investments,
            "get_budget_status": self.get_budget_status,
        }
    
    def get_function_definitions(self):
        """Return OpenAI-compatible function definitions"""
        return [
            {
                "name": "add_expense",
                "description": "Add a new expense to WealthPulse",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Expense title"},
                        "amount": {"type": "number", "description": "Expense amount"},
                        "category": {"type": "string", "description": "Category name"},
                        "payment_method": {"type": "string", "description": "Payment method name"},
                        "description": {"type": "string", "description": "Optional description"},
                        "date": {"type": "string", "description": "Date in YYYY-MM-DD format (optional)"},
                    },
                    "required": ["title", "amount", "category", "payment_method"],
                },
            },
            {
                "name": "list_expenses",
                "description": "Get a list of expenses with optional filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of expenses (default 10)"},
                        "category": {"type": "string", "description": "Filter by category"},
                        "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                        "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                    },
                },
            },
            {
                "name": "get_expense_summary",
                "description": "Get spending summary and statistics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {"type": "string", "enum": ["month", "year", "all"], "description": "Time period"},
                    },
                },
            },
            {
                "name": "list_categories",
                "description": "Get all expense categories",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "add_category",
                "description": "Create a new expense category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Category name"},
                        "description": {"type": "string", "description": "Category description"},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "add_investment",
                "description": "Add a new investment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Investment name"},
                        "investment_type": {"type": "string", "description": "Investment type"},
                        "amount": {"type": "number", "description": "Investment amount"},
                        "current_value": {"type": "number", "description": "Current value (optional)"},
                    },
                    "required": ["name", "investment_type", "amount"],
                },
            },
            {
                "name": "list_investments",
                "description": "Get all investments",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_budget_status",
                "description": "Get current budget status and remaining budget",
                "parameters": {"type": "object", "properties": {}},
            },
        ]
    
    def add_expense(self, title, amount, category, payment_method, description="", date=None):
        """Add a new expense"""
        # Get or create category
        cat = Category.query.filter_by(user_id=self.user_id, name=category).first()
        if not cat:
            cat = Category(user_id=self.user_id, name=category)
            db.session.add(cat)
            db.session.flush()
        
        # Get or create payment method
        pm = PaymentMethod.query.filter_by(user_id=self.user_id, name=payment_method).first()
        if not pm:
            pm = PaymentMethod(user_id=self.user_id, name=payment_method)
            db.session.add(pm)
            db.session.flush()
        
        # Parse date
        expense_date = datetime.today().date()
        if date:
            expense_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Create expense
        expense = Expense(
            user_id=self.user_id,
            title=title,
            amount=amount,
            category_id=cat.id,
            payment_method_id=pm.id,
            description=description,
            date=expense_date
        )
        db.session.add(expense)
        db.session.commit()
        
        return f"✅ Added expense: {title} - {self.user.currency} {amount:.2f} ({category})"
    
    def list_expenses(self, limit=10, category=None, start_date=None, end_date=None):
        """List expenses with filters"""
        query = Expense.query.filter_by(user_id=self.user_id)
        
        if category:
            cat = Category.query.filter_by(user_id=self.user_id, name=category).first()
            if cat:
                query = query.filter_by(category_id=cat.id)
        
        if start_date:
            query = query.filter(Expense.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
        
        if end_date:
            query = query.filter(Expense.date <= datetime.strptime(end_date, "%Y-%m-%d").date())
        
        expenses = query.order_by(Expense.date.desc()).limit(limit).all()
        
        if not expenses:
            return "No expenses found."
        
        result = f"📊 Found {len(expenses)} expense(s):\n\n"
        for exp in expenses:
            result += f"• {exp.date} - {exp.title}: {self.user.currency} {exp.amount:.2f} ({exp.category.name})\n"
        
        total = sum(e.amount for e in expenses)
        result += f"\n💰 Total: {self.user.currency} {total:.2f}"
        
        return result
    
    def get_expense_summary_for_dates(self, start_date_str, end_date_str):
        """Get spending summary for specific date range"""
        query = Expense.query.filter_by(user_id=self.user_id)
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        query = query.filter(Expense.date >= start_date, Expense.date <= end_date)
        expenses = query.all()
        
        if not expenses:
            if start_date == end_date:
                period_name = start_date.strftime("%B %d, %Y")
            else:
                period_name = f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"
            return f"No expenses found for {period_name}."
        
        total = sum(e.amount for e in expenses)
        avg = total / len(expenses)
        
        # Category breakdown
        category_totals = {}
        for exp in expenses:
            cat_name = exp.category.name
            category_totals[cat_name] = category_totals.get(cat_name, 0) + exp.amount
        
        if start_date == end_date:
            period_name = start_date.strftime("%B %d, %Y")
        else:
            period_name = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        
        result = f"📈 Expense Summary - {period_name}\n\n"
        result += f"Total: {self.user.currency} {total:.2f}\n"
        result += f"Count: {len(expenses)} expenses\n"
        result += f"Average: {self.user.currency} {avg:.2f}\n\n"
        result += "By Category:\n"
        for cat, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (amt / total) * 100
            result += f"  • {cat}: {self.user.currency} {amt:.2f} ({pct:.1f}%)\n"
        
        return result
    
    def get_expense_summary(self, period="month"):
        """Get spending summary"""
        query = Expense.query.filter_by(user_id=self.user_id)
        
        today = date.today()
        if period == "month":
            start_date = today.replace(day=1)
            query = query.filter(Expense.date >= start_date)
            period_name = today.strftime("%B %Y")
        elif period == "year":
            start_date = today.replace(month=1, day=1)
            query = query.filter(Expense.date >= start_date)
            period_name = str(today.year)
        else:
            period_name = "All Time"
        
        expenses = query.all()
        
        if not expenses:
            return f"No expenses found for {period_name}."
        
        total = sum(e.amount for e in expenses)
        avg = total / len(expenses)
        
        # Category breakdown
        category_totals = {}
        for exp in expenses:
            cat_name = exp.category.name
            category_totals[cat_name] = category_totals.get(cat_name, 0) + exp.amount
        
        result = f"📈 Expense Summary - {period_name}\n\n"
        result += f"Total: {self.user.currency} {total:.2f}\n"
        result += f"Count: {len(expenses)} expenses\n"
        result += f"Average: {self.user.currency} {avg:.2f}\n\n"
        result += "By Category:\n"
        for cat, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (amt / total) * 100
            result += f"  • {cat}: {self.user.currency} {amt:.2f} ({pct:.1f}%)\n"
        
        if self.user.monthly_budget > 0 and period == "month":
            remaining = self.user.monthly_budget - total
            pct_used = (total / self.user.monthly_budget) * 100
            result += f"\n💳 Budget: {self.user.currency} {self.user.monthly_budget:.2f}\n"
            result += f"Remaining: {self.user.currency} {remaining:.2f} ({pct_used:.1f}% used)"
        
        return result
    
    def list_categories(self):
        """List all categories"""
        categories = Category.query.filter_by(user_id=self.user_id).all()
        
        if not categories:
            return "No categories found."
        
        result = "📁 Categories:\n\n"
        for cat in categories:
            result += f"• {cat.name}"
            if cat.description:
                result += f": {cat.description}"
            result += "\n"
        
        return result
    
    def add_category(self, name, description=""):
        """Add a new category"""
        existing = Category.query.filter_by(user_id=self.user_id, name=name).first()
        
        if existing:
            return f"❌ Category '{name}' already exists."
        
        category = Category(user_id=self.user_id, name=name, description=description)
        db.session.add(category)
        db.session.commit()
        
        return f"✅ Created category: {name}"
    
    def add_investment(self, name, investment_type, amount, current_value=None):
        """Add a new investment"""
        # Get or create investment type
        inv_type = InvestmentType.query.filter_by(user_id=self.user_id, name=investment_type).first()
        if not inv_type:
            inv_type = InvestmentType(user_id=self.user_id, name=investment_type)
            db.session.add(inv_type)
            db.session.flush()
        
        investment = Investment(
            user_id=self.user_id,
            name=name,
            investment_type_id=inv_type.id,
            amount=amount,
            current_value=current_value or amount
        )
        db.session.add(investment)
        db.session.commit()
        
        return f"✅ Added investment: {name} - {self.user.currency} {amount:.2f} ({investment_type})"
    
    def list_investments(self):
        """List all investments"""
        investments = Investment.query.filter_by(user_id=self.user_id).order_by(Investment.created_at.desc()).all()
        
        if not investments:
            return "No investments found."
        
        result = "💼 Investments:\n\n"
        total_invested = 0
        total_current = 0
        
        for inv in investments:
            returns = inv.current_value - inv.amount if inv.current_value else 0
            returns_pct = (returns / inv.amount) * 100 if inv.amount > 0 else 0
            returns_sign = "📈" if returns >= 0 else "📉"
            current_val = inv.current_value if inv.current_value else inv.amount
            
            result += f"• {inv.name} ({inv.type.name})\n"
            result += f"  Invested: {self.user.currency} {inv.amount:.2f} | Current: {self.user.currency} {current_val:.2f}\n"
            result += f"  Returns: {returns_sign} {self.user.currency} {returns:.2f} ({returns_pct:+.2f}%)\n\n"
            
            total_invested += inv.amount
            total_current += current_val
        
        total_returns = total_current - total_invested
        total_returns_pct = (total_returns / total_invested) * 100 if total_invested > 0 else 0
        
        result += f"📊 Total Invested: {self.user.currency} {total_invested:.2f}\n"
        result += f"💰 Current Value: {self.user.currency} {total_current:.2f}\n"
        result += f"📈 Total Returns: {self.user.currency} {total_returns:.2f} ({total_returns_pct:+.2f}%)"
        
        return result
    
    def get_budget_status(self):
        """Get budget status"""
        if self.user.monthly_budget <= 0:
            return "No monthly budget set."
        
        today = date.today()
        start_of_month = today.replace(day=1)
        
        total_spent = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == self.user_id,
            Expense.date >= start_of_month,
            Expense.date <= today
        ).scalar() or 0
        
        remaining = self.user.monthly_budget - total_spent
        pct_used = (total_spent / self.user.monthly_budget) * 100
        
        result = f"💳 Budget Status - {today.strftime('%B %Y')}\n\n"
        result += f"Budget: {self.user.currency} {self.user.monthly_budget:.2f}\n"
        result += f"Spent: {self.user.currency} {total_spent:.2f} ({pct_used:.1f}%)\n"
        result += f"Remaining: {self.user.currency} {remaining:.2f}\n\n"
        
        if remaining < 0:
            result += "⚠️ Over budget!"
        elif pct_used > 90:
            result += "⚠️ Warning: Over 90% of budget used!"
        elif pct_used > 75:
            result += "⚠️ Over 75% of budget used"
        else:
            result += "✅ Within budget"
        
        return result
    
    def generate_spending_chart_for_dates(self, start_date_str, end_date_str, chart_type="category"):
        """Generate spending charts for specific date range"""
        query = Expense.query.filter_by(user_id=self.user_id)
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        query = query.filter(Expense.date >= start_date, Expense.date <= end_date)
        expenses = query.all()
        
        if not expenses:
            if start_date == end_date:
                period_name = start_date.strftime("%B %d, %Y")
            else:
                period_name = f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"
            return None, f"No expenses found for {period_name} to generate chart."
        
        if start_date == end_date:
            period_name = start_date.strftime("%B %d, %Y")
        else:
            period_name = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == "category":
            # Pie chart by category
            category_totals = defaultdict(float)
            for exp in expenses:
                category_totals[exp.category.name] += exp.amount
            
            categories = list(category_totals.keys())
            amounts = list(category_totals.values())
            colors = plt.cm.Set3(range(len(categories)))
            
            ax.pie(amounts, labels=categories, autopct='%1.1f%%', colors=colors, startangle=90)
            ax.set_title(f'Spending by Category - {period_name}', fontsize=14, fontweight='bold')
            
        elif chart_type == "timeline":
            # Line chart over time
            date_totals = defaultdict(float)
            for exp in expenses:
                date_totals[exp.date] += exp.amount
            
            dates = sorted(date_totals.keys())
            amounts = [date_totals[d] for d in dates]
            
            ax.plot(dates, amounts, marker='o', linewidth=2, markersize=6, color='#8B0000')
            ax.fill_between(dates, amounts, alpha=0.3, color='#8B0000')
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel(f'Amount ({self.user.currency})', fontsize=12)
            ax.set_title(f'Daily Spending - {period_name}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha='right')
            
        elif chart_type == "comparison":
            # Bar chart by category
            category_totals = defaultdict(float)
            for exp in expenses:
                category_totals[exp.category.name] += exp.amount
            
            categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            cat_names = [c[0] for c in categories]
            amounts = [c[1] for c in categories]
            
            bars = ax.barh(cat_names, amounts, color='#8B0000', alpha=0.8)
            ax.set_xlabel(f'Amount ({self.user.currency})', fontsize=12)
            ax.set_title(f'Spending by Category - {period_name}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='x')
            
            # Add value labels on bars
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2, 
                       f'{self.user.currency} {width:.0f}',
                       ha='left', va='center', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        
        return image_base64, None
    
    def generate_spending_chart(self, period="month", chart_type="category"):
        """
        Generate spending charts as base64 encoded images
        chart_type: 'category' (pie chart), 'timeline' (line chart), 'comparison' (bar chart)
        """
        query = Expense.query.filter_by(user_id=self.user_id)
        
        today = date.today()
        if period == "month":
            start_date = today.replace(day=1)
            query = query.filter(Expense.date >= start_date)
            period_name = today.strftime("%B %Y")
        elif period == "year":
            start_date = today.replace(month=1, day=1)
            query = query.filter(Expense.date >= start_date)
            period_name = str(today.year)
        else:
            period_name = "All Time"
        
        expenses = query.all()
        
        if not expenses:
            return None, f"No expenses found for {period_name} to generate chart."
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == "category":
            # Pie chart by category
            category_totals = defaultdict(float)
            for exp in expenses:
                category_totals[exp.category.name] += exp.amount
            
            categories = list(category_totals.keys())
            amounts = list(category_totals.values())
            colors = plt.cm.Set3(range(len(categories)))
            
            ax.pie(amounts, labels=categories, autopct='%1.1f%%', colors=colors, startangle=90)
            ax.set_title(f'Spending by Category - {period_name}', fontsize=14, fontweight='bold')
            
        elif chart_type == "timeline":
            # Line chart over time
            date_totals = defaultdict(float)
            for exp in expenses:
                date_totals[exp.date] += exp.amount
            
            dates = sorted(date_totals.keys())
            amounts = [date_totals[d] for d in dates]
            
            ax.plot(dates, amounts, marker='o', linewidth=2, markersize=6, color='#8B0000')
            ax.fill_between(dates, amounts, alpha=0.3, color='#8B0000')
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel(f'Amount ({self.user.currency})', fontsize=12)
            ax.set_title(f'Daily Spending - {period_name}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha='right')
            
        elif chart_type == "comparison":
            # Bar chart by category
            category_totals = defaultdict(float)
            for exp in expenses:
                category_totals[exp.category.name] += exp.amount
            
            categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            cat_names = [c[0] for c in categories]
            amounts = [c[1] for c in categories]
            
            bars = ax.barh(cat_names, amounts, color='#8B0000', alpha=0.8)
            ax.set_xlabel(f'Amount ({self.user.currency})', fontsize=12)
            ax.set_title(f'Spending by Category - {period_name}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='x')
            
            # Add value labels on bars
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2, 
                       f'{self.user.currency} {width:.0f}',
                       ha='left', va='center', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        
        return image_base64, None
