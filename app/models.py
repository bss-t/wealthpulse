from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    monthly_budget = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    expenses = db.relationship('Expense', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    investments = db.relationship('Investment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_total_expenses_this_month(self):
        """Get total expenses for current month"""
        today = date.today()
        start_of_month = today.replace(day=1)
        return db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.user_id == self.id,
            Expense.date >= start_of_month,
            Expense.date <= today
        ).scalar() or 0.0

    def get_remaining_budget(self):
        """Get remaining budget for current month"""
        return self.monthly_budget - self.get_total_expenses_this_month()

    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50), default='fas fa-tag')
    color = db.Column(db.String(20), default='primary')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null for system categories
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    expenses = db.relationship('Expense', backref='category', lazy='dynamic')

    def get_total_amount_this_month(self):
        """Get total amount spent in this category this month"""
        today = date.today()
        start_of_month = today.replace(day=1)
        return db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.category_id == self.id,
            Expense.date >= start_of_month,
            Expense.date <= today
        ).scalar() or 0.0

    def __repr__(self):
        return f'<Category {self.name}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    payment_method = db.Column(db.String(50), default='cash')  # Legacy field - kept for backward compatibility
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_method.id'))
    receipt_filename = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    payment_method_obj = db.relationship('PaymentMethod', backref='expenses', foreign_keys=[payment_method_id])
    
    @property
    def receipt(self):
        """Alias for receipt_filename for backward compatibility"""
        return self.receipt_filename
    
    @receipt.setter
    def receipt(self, value):
        """Allow setting receipt via the property"""
        self.receipt_filename = value
    
    def get_payment_method_name(self):
        """Get payment method name from either new or old field"""
        if self.payment_method_obj:
            return self.payment_method_obj.name
        return self.payment_method.replace('_', ' ').title() if self.payment_method else 'Unknown'

    def __repr__(self):
        return f'<Expense {self.title}: ${self.amount}>'

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    category = db.relationship('Category', backref='budgets')

    @property
    def spent(self):
        """Get amount spent in this category for this period"""
        return db.session.query(func.sum(Expense.amount)).filter(
            Expense.category_id == self.category_id,
            Expense.user_id == self.user_id,
            Expense.date >= self.start_date,
            Expense.date <= self.end_date
        ).scalar() or 0.0

    @property
    def remaining(self):
        """Get remaining budget amount"""
        return self.amount - self.spent

    @property
    def percentage_used(self):
        """Get percentage of budget used"""
        if self.amount == 0:
            return 0
        return (self.spent / self.amount) * 100

    @property
    def is_active(self):
        """Check if budget period is currently active"""
        today = datetime.now().date()
        return self.start_date <= today <= self.end_date

    @property
    def days_remaining(self):
        """Get number of days remaining in budget period"""
        today = datetime.now().date()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days

    @property
    def recent_expenses(self):
        """Get recent expenses for this budget's category"""
        return Expense.query.filter(
            Expense.category_id == self.category_id,
            Expense.user_id == self.user_id,
            Expense.date >= self.start_date,
            Expense.date <= self.end_date
        ).order_by(Expense.date.desc()).limit(5).all()

    def __repr__(self):
        return f'<Budget {self.category.name}: ${self.amount}>'
class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50), default='fas fa-credit-card')
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PaymentMethod {self.name}>'

class InvestmentType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50), default='fas fa-chart-line')
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null for system defaults
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    investments = db.relationship('Investment', backref='type', lazy='dynamic')

    def __repr__(self):
        return f'<InvestmentType {self.name}>'

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    investment_type_id = db.Column(db.Integer, db.ForeignKey('investment_type.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    investment_date = db.Column(db.Date, nullable=False, default=date.today)
    expected_return = db.Column(db.Float)  # Expected return percentage
    maturity_date = db.Column(db.Date)  # Optional maturity date
    current_value = db.Column(db.Float)  # Current value of investment
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_return_percentage(self):
        """Calculate actual return percentage if current value is available"""
        if self.current_value and self.amount > 0:
            return ((self.current_value - self.amount) / self.amount) * 100
        return 0.0

    def get_profit_loss(self):
        """Calculate profit or loss"""
        if self.current_value:
            return self.current_value - self.amount
        return 0.0

    def __repr__(self):
        return f'<Investment {self.name}: ${self.amount}>'

class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    response_type = db.Column(db.String(20), default='text')  # 'text' or 'image'
    image_data = db.Column(db.Text)  # Base64 encoded image for charts
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatMessage {self.id}: {self.message[:30]}...>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

