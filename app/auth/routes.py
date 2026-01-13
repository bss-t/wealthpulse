from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime
from app.auth import bp
from app.models import User
from app.forms import LoginForm, RegistrationForm
from app import db

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Allow login with either username or email
        user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.username.data)
        ).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact administrator.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Update last login timestamp
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.dashboard')
        
        flash(f'Welcome back, {user.get_full_name()}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            currency=form.currency.data,
            monthly_budget=form.monthly_budget.data or 0.0
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # Create default categories for the new user
        from app.models import Category, PaymentMethod, InvestmentType
        default_categories = [
            {'name': 'Food & Dining', 'icon': 'fas fa-utensils', 'color': 'success'},
            {'name': 'Transportation', 'icon': 'fas fa-car', 'color': 'primary'},
            {'name': 'Housing & Utilities', 'icon': 'fas fa-home', 'color': 'info'},
            {'name': 'Shopping', 'icon': 'fas fa-shopping-bag', 'color': 'warning'},
            {'name': 'Entertainment', 'icon': 'fas fa-gamepad', 'color': 'purple'},
            {'name': 'Healthcare', 'icon': 'fas fa-heartbeat', 'color': 'danger'},
            {'name': 'Education', 'icon': 'fas fa-graduation-cap', 'color': 'dark'},
            {'name': 'Other', 'icon': 'fas fa-tag', 'color': 'secondary'}
        ]
        
        for cat_data in default_categories:
            category = Category(
                name=cat_data['name'],
                icon=cat_data['icon'],
                color=cat_data['color'],
                user_id=user.id,
                is_default=(cat_data['name'] == 'Other')  # Only 'Other' is truly default
            )
            db.session.add(category)
        
        # Create default payment methods for the new user
        default_payment_methods = [
            {'name': 'Cash', 'icon': 'fas fa-money-bill-wave', 'description': 'Cash payments'},
            {'name': 'Debit Card', 'icon': 'fas fa-credit-card', 'description': 'Debit card transactions'},
            {'name': 'Credit Card', 'icon': 'fas fa-credit-card', 'description': 'Credit card transactions'},
            {'name': 'UPI', 'icon': 'fas fa-mobile-alt', 'description': 'UPI payments'},
            {'name': 'Digital Wallet', 'icon': 'fas fa-wallet', 'description': 'Digital wallet payments'},
            {'name': 'Bank Transfer', 'icon': 'fas fa-university', 'description': 'Bank transfers'},
            {'name': 'Other', 'icon': 'fas fa-ellipsis-h', 'description': 'Other payment methods'}
        ]
        
        for pm_data in default_payment_methods:
            payment_method = PaymentMethod(
                name=pm_data['name'],
                icon=pm_data['icon'],
                description=pm_data['description'],
                user_id=user.id,
                is_default=True
            )
            db.session.add(payment_method)
        
        # Create default investment types for the new user
        default_investment_types = [
            {'name': 'Stocks', 'icon': 'fas fa-chart-line', 'description': 'Stock market investments'},
            {'name': 'Mutual Funds', 'icon': 'fas fa-chart-pie', 'description': 'Mutual fund investments'},
            {'name': 'Fixed Deposit', 'icon': 'fas fa-landmark', 'description': 'Bank fixed deposits'},
            {'name': 'Bonds', 'icon': 'fas fa-university', 'description': 'Government and corporate bonds'},
            {'name': 'Real Estate', 'icon': 'fas fa-building', 'description': 'Property investments'},
            {'name': 'Gold', 'icon': 'fas fa-gem', 'description': 'Gold and precious metals'},
            {'name': 'Cryptocurrency', 'icon': 'fas fa-bitcoin', 'description': 'Digital currencies'},
            {'name': 'PPF', 'icon': 'fas fa-piggy-bank', 'description': 'Public Provident Fund'},
            {'name': 'Other', 'icon': 'fas fa-coins', 'description': 'Other investments'}
        ]
        
        for it_data in default_investment_types:
            investment_type = InvestmentType(
                name=it_data['name'],
                icon=it_data['icon'],
                description=it_data['description'],
                user_id=user.id,
                is_default=(it_data['name'] == 'Other')
            )
            db.session.add(investment_type)
        
        db.session.commit()
        
        flash(f'Registration successful! Welcome {user.get_full_name()}!', 'success')
        login_user(user)
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/register.html', title='Register', form=form)