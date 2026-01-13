from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, FloatField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional
from datetime import date
from app.models import User, Category

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    currency = SelectField('Currency', choices=[
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('JPY', 'JPY - Japanese Yen'),
        ('CAD', 'CAD - Canadian Dollar'),
        ('AUD', 'AUD - Australian Dollar'),
        ('INR', 'INR - Indian Rupee')
    ], default='USD')
    monthly_budget = FloatField('Monthly Budget (Optional)', validators=[NumberRange(min=0)], default=0)
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ExpenseForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    payment_method = SelectField('Payment Method', coerce=int, validators=[DataRequired()])
    receipt = FileField('Receipt (Optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf'], 'Images and PDFs only!')
    ])
    submit = SubmitField('Save Expense')

    def __init__(self, user_id=None, *args, **kwargs):
        super(ExpenseForm, self).__init__(*args, **kwargs)
        if user_id:
            from app.models import PaymentMethod
            self.category_id.choices = [
                (c.id, c.name) for c in Category.query.filter_by(user_id=user_id).order_by(Category.name).all()
            ]
            self.payment_method.choices = [
                (pm.id, pm.name) for pm in PaymentMethod.query.filter_by(user_id=user_id, is_active=True).order_by(PaymentMethod.name).all()
            ]

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    icon = SelectField('Icon', choices=[
        ('fas fa-utensils', '🍽️ Food & Dining'),
        ('fas fa-car', '🚗 Transportation'),
        ('fas fa-home', '🏠 Housing'),
        ('fas fa-shopping-bag', '🛍️ Shopping'),
        ('fas fa-gamepad', '🎮 Entertainment'),
        ('fas fa-heartbeat', '💊 Healthcare'),
        ('fas fa-graduation-cap', '📚 Education'),
        ('fas fa-briefcase', '💼 Business'),
        ('fas fa-plane', '✈️ Travel'),
        ('fas fa-tshirt', '👕 Clothing'),
        ('fas fa-mobile-alt', '📱 Technology'),
        ('fas fa-dumbbell', '🏃 Fitness'),
        ('fas fa-tag', '🏷️ Other')
    ], default='fas fa-tag')
    color = SelectField('Color', choices=[
        ('primary', 'Blue'),
        ('success', 'Green'),
        ('danger', 'Red'),
        ('warning', 'Yellow'),
        ('info', 'Cyan'),
        ('secondary', 'Gray'),
        ('dark', 'Dark'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('pink', 'Pink')
    ], default='primary')
    submit = SubmitField('Save Category')

class BudgetForm(FlaskForm):
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    amount = FloatField('Budget Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    start_date = DateField('Start Date', validators=[DataRequired()], default=date.today)
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Save Budget')

    def __init__(self, user_id=None, *args, **kwargs):
        super(BudgetForm, self).__init__(*args, **kwargs)
        if user_id:
            self.category_id.choices = [
                (c.id, c.name) for c in Category.query.filter_by(user_id=user_id).order_by(Category.name).all()
            ]
        
        # Set default end date to end of current month if not set
        if not self.end_date.data:
            from datetime import date
            today = date.today()
            import calendar
            last_day = calendar.monthrange(today.year, today.month)[1]
            self.end_date.data = date(today.year, today.month, last_day)

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    currency = SelectField('Currency', choices=[
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('JPY', 'JPY - Japanese Yen'),
        ('CAD', 'CAD - Canadian Dollar'),
        ('AUD', 'AUD - Australian Dollar'),
        ('INR', 'INR - Indian Rupee')
    ])
    monthly_budget = FloatField('Monthly Budget', validators=[NumberRange(min=0)])
    submit = SubmitField('Update Profile')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Please use a different email address.')

class InvestmentForm(FlaskForm):
    name = StringField('Investment Name', validators=[DataRequired(), Length(max=100)])
    investment_type_id = SelectField('Investment Type', coerce=int, validators=[DataRequired()])
    amount = FloatField('Investment Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    investment_date = DateField('Investment Date', format='%Y-%m-%d', validators=[DataRequired()])
    expected_return = FloatField('Expected Return (%)', validators=[Optional(), NumberRange(min=0)])
    maturity_date = DateField('Maturity Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    current_value = FloatField('Current Value (Optional)', validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Investment')
    
    def __init__(self, user_id=None, *args, **kwargs):
        super(InvestmentForm, self).__init__(*args, **kwargs)
        from app.models import InvestmentType
        if user_id:
            self.investment_type_id.choices = [
                (t.id, t.name) for t in InvestmentType.query.filter(
                    (InvestmentType.user_id == user_id) | (InvestmentType.user_id == None),
                    InvestmentType.is_active == True
                ).order_by(InvestmentType.name).all()
            ]

class InvestmentTypeForm(FlaskForm):
    name = StringField('Type Name', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=200)])
    icon = SelectField('Icon', choices=[
        ('fas fa-chart-line', '📈 Chart Line'),
        ('fas fa-coins', '🪙 Coins'),
        ('fas fa-piggy-bank', '🐷 Piggy Bank'),
        ('fas fa-landmark', '🏛️ Landmark/Bank'),
        ('fas fa-building', '🏢 Building/Real Estate'),
        ('fas fa-gem', '💎 Gem/Gold'),
        ('fas fa-bitcoin', '₿ Bitcoin/Crypto'),
        ('fas fa-university', '🏦 University/Institution'),
        ('fas fa-hand-holding-usd', '💰 Hand Holding USD'),
        ('fas fa-donate', '💸 Donate'),
        ('fas fa-money-bill-wave', '💵 Money Bill'),
        ('fas fa-chart-pie', '📊 Chart Pie'),
        ('fas fa-wallet', '👛 Wallet'),
        ('fas fa-briefcase', '💼 Briefcase')
    ], default='fas fa-chart-line')
    submit = SubmitField('Save Type')

class StatementUploadForm(FlaskForm):
    statement_file = FileField('Bank/Credit Card Statement (PDF)', validators=[
        DataRequired(),
        FileAllowed(['pdf'], 'Only PDF files are allowed!')
    ])
    pdf_password = StringField('PDF Password (if protected)', validators=[Optional(), Length(max=50)])
    default_category_id = SelectField('Default Category', coerce=int, validators=[DataRequired()])
    default_payment_method = SelectField('Default Payment Method', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Upload & Parse Statement')

class DeleteAccountForm(FlaskForm):
    confirmation = StringField("Type DELETE to confirm", validators=[DataRequired()])
    submit = SubmitField("Delete My Account")

