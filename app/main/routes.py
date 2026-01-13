from flask import render_template, redirect, url_for, flash, request, jsonify, send_from_directory, current_app, Response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from werkzeug.utils import secure_filename
import calendar
import os
import csv
from io import StringIO

from app.main import bp
from app.models import User, Expense, Category, Budget, PaymentMethod, Investment, InvestmentType
from app.forms import EditProfileForm, ExpenseForm, CategoryForm, BudgetForm, DeleteAccountForm
from app import db

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    # Get current month expenses
    start_of_month = today.replace(day=1)
    current_month_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_of_month,
        Expense.date <= today
    ).all()
    
    # Calculate statistics
    total_this_month = sum([exp.amount for exp in current_month_expenses])
    expense_count = len(current_month_expenses)
    
    # Get remaining budget
    remaining_budget = current_user.get_remaining_budget()
    budget_percentage = 0
    if current_user.monthly_budget > 0:
        budget_percentage = (total_this_month / current_user.monthly_budget) * 100
    
    # Get recent expenses (last 5)
    recent_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(
        Expense.created_at.desc()
    ).limit(5).all()
    
    # Get category spending for current month
    category_spending = db.session.query(
        Category.name,
        Category.icon,
        Category.color,
        func.sum(Expense.amount).label('total_amount'),
        func.count(Expense.id).label('expense_count')
    ).join(Expense).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_of_month,
        Expense.date <= today
    ).group_by(Category.id).order_by(func.sum(Expense.amount).desc()).limit(6).all()
    
    # Get daily spending for current month (for chart)
    daily_spending_query = db.session.query(
        Expense.date,
        func.sum(Expense.amount).label('daily_total')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_of_month,
        Expense.date <= today
    ).group_by(Expense.date).order_by(Expense.date).all()
    
    # Convert to list of dictionaries for JSON serialization
    daily_spending = [{'date': str(row.date), 'daily_total': float(row.daily_total)} for row in daily_spending_query]
    
    # Get recent investments (last 5)
    recent_investments = Investment.query.filter_by(user_id=current_user.id).order_by(
        Investment.created_at.desc()
    ).limit(5).all()
    
    # Get investment distribution by type
    investment_distribution = db.session.query(
        InvestmentType.name,
        InvestmentType.icon,
        func.sum(Investment.amount).label('total_amount'),
        func.count(Investment.id).label('investment_count')
    ).join(Investment).filter(
        Investment.user_id == current_user.id
    ).group_by(InvestmentType.id).order_by(func.sum(Investment.amount).desc()).all()
    
    # Calculate total investment value
    total_invested = sum([inv.amount for inv in Investment.query.filter_by(user_id=current_user.id).all()])
    total_current_value = sum([inv.current_value or inv.amount for inv in Investment.query.filter_by(user_id=current_user.id).all()])
    investment_returns = total_current_value - total_invested
    
    return render_template('main/dashboard.html',
                         title='Dashboard',
                         today_date=today.strftime('%A, %B %d, %Y'),
                         total_this_month=total_this_month,
                         expense_count=expense_count,
                         remaining_budget=remaining_budget,
                         budget_percentage=min(budget_percentage, 100),
                         recent_expenses=recent_expenses,
                         category_spending=category_spending,
                         daily_spending=daily_spending,
                         current_month=today.strftime('%B %Y'),
                         recent_investments=recent_investments,
                         investment_distribution=investment_distribution,
                         total_invested=total_invested,
                         total_current_value=total_current_value,
                         investment_returns=investment_returns)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = EditProfileForm(current_user.username, current_user.email)
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.currency = form.currency.data
        current_user.monthly_budget = form.monthly_budget.data
        
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('main.profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.currency.data = current_user.currency
        form.monthly_budget.data = current_user.monthly_budget
    
    # Get user statistics
    total_expenses = Expense.query.filter_by(user_id=current_user.id).count()
    total_amount = db.session.query(func.sum(Expense.amount)).filter_by(user_id=current_user.id).scalar() or 0
    categories_count = Category.query.filter_by(user_id=current_user.id).count()
    active_budgets = Budget.query.filter_by(user_id=current_user.id).count()
    
    user_stats = {
        'total_expenses': total_expenses,
        'total_amount': total_amount,
        'categories_used': categories_count,
        'active_budgets': active_budgets
    }
    
    # Get monthly spending for last 6 months
    monthly_data = []
    for i in range(6):
        month_date = date.today().replace(day=1) - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        month_end = month_date.replace(day=calendar.monthrange(month_date.year, month_date.month)[1])
        
        month_total = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date >= month_start,
            Expense.date <= month_end
        ).scalar() or 0
        
        monthly_data.append({
            'month': month_date.strftime('%b %Y'),
            'total': month_total
        })
    
    monthly_data.reverse()  # Show oldest to newest
    
    return render_template('main/profile.html',
                         title='Profile',
                         form=form,
                         user=current_user,
                         user_stats=user_stats,
                         monthly_data=monthly_data)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username, current_user.email)
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.currency = form.currency.data
        current_user.monthly_budget = form.monthly_budget.data
        
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('main.profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.currency.data = current_user.currency
        form.monthly_budget.data = current_user.monthly_budget
    
    return render_template('main/edit_profile.html', title='Edit Profile', form=form)

@bp.route('/export_data')
@login_required
def export_data():
    """Export user expenses and investments to CSV format"""
    export_type = request.args.get('type', 'expenses')
    
    si = StringIO()
    writer = csv.writer(si)
    
    if export_type == 'investments':
        # Get all investments for the user
        investments = Investment.query.filter_by(user_id=current_user.id).order_by(Investment.investment_date.desc()).all()
        
        # Write header
        writer.writerow(['Date', 'Name', 'Type', 'Amount', 'Current Value', 'Returns', 'Expected Return %', 'Maturity Date', 'Notes'])
        
        # Write investment data
        for inv in investments:
            current_value = inv.current_value or inv.amount
            returns = current_value - inv.amount
            writer.writerow([
                inv.investment_date.strftime('%Y-%m-%d'),
                inv.name,
                inv.type.name if inv.type else 'N/A',
                f"{inv.amount:.2f}",
                f"{current_value:.2f}",
                f"{returns:.2f}",
                f"{inv.expected_return:.2f}" if inv.expected_return else '',
                inv.maturity_date.strftime('%Y-%m-%d') if inv.maturity_date else '',
                inv.notes or ''
            ])
        
        filename = f'investments_{datetime.now().strftime("%Y%m%d")}.csv'
    else:
        # Get all expenses for the user
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
        
        # Write header
        writer.writerow(['Date', 'Title', 'Description', 'Amount', 'Category', 'Payment Method'])
        
        # Write expense data
        for expense in expenses:
            writer.writerow([
                expense.date.strftime('%Y-%m-%d'),
                expense.title,
                expense.description or '',
                f"{expense.amount:.2f}",
                expense.category.name if expense.category else 'N/A',
                expense.payment_method
            ])
        
        filename = f'expenses_{datetime.now().strftime("%Y%m%d")}.csv'
    
    # Create response
    output = si.getvalue()
    si.close()
    
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@bp.route('/reports')
@login_required
def reports():
    # Get filter parameters
    period = request.args.get('period', 'current_month')
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    category_id = request.args.get('category', type=int)
    
    # Handle period-based filtering
    today = date.today()
    
    if period == 'current_month' or (not start_date or not end_date or start_date == '' or end_date == ''):
        start = today.replace(day=1)
        end = today
        start_date = start.strftime('%Y-%m-%d')
        end_date = end.strftime('%Y-%m-%d')
    else:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format', 'danger')
            start = today.replace(day=1)
            end = today
            start_date = start.strftime('%Y-%m-%d')
            end_date = end.strftime('%Y-%m-%d')
    
    # Base query for the period
    query = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start,
        Expense.date <= end
    )
    
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    
    expenses = query.all()
    
    # Calculate totals
    total_amount = sum([exp.amount for exp in expenses])
    total_count = len(expenses)
    
    # Category breakdown
    category_totals = db.session.query(
        Category.name,
        Category.icon,
        Category.color,
        func.sum(Expense.amount).label('total'),
        func.count(Expense.id).label('count')
    ).join(Expense).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start,
        Expense.date <= end
    )
    
    if category_id:
        category_totals = category_totals.filter(Expense.category_id == category_id)
    
    category_totals = category_totals.group_by(Category.id).order_by(
        func.sum(Expense.amount).desc()
    ).all()
    
    # Payment method breakdown
    payment_totals = db.session.query(
        Expense.payment_method,
        func.sum(Expense.amount).label('total'),
        func.count(Expense.id).label('count')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start,
        Expense.date <= end
    )
    
    if category_id:
        payment_totals = payment_totals.filter(Expense.category_id == category_id)
    
    payment_totals = payment_totals.group_by(Expense.payment_method).order_by(
        func.sum(Expense.amount).desc()
    ).all()
    
    # Create summary object
    summary = {
        'total_expenses': total_amount,
        'expense_count': total_count,
        'avg_expense': total_amount / total_count if total_count > 0 else 0,
        'categories_used': len(category_totals)
    }
    
    # Get categories for filter
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.is_default == True)
    ).order_by(Category.name).all()
    
    # Format category_stats for charts (convert SQLAlchemy Row to dict-like objects)
    category_stats = []
    for cat in category_totals:
        percentage = (float(cat.total) / total_amount * 100) if total_amount > 0 else 0
        category_stats.append({
            'name': cat.name,
            'icon': cat.icon,
            'color': cat.color,
            'total': float(cat.total),
            'count': cat.count,
            'percentage': percentage
        })
    
    # Format payment_methods for charts
    payment_methods = []
    for payment in payment_totals:
        payment_methods.append({
            'method': payment.payment_method,
            'total': float(payment.total),
            'count': payment.count
        })
    
    # Get trend data (daily spending over the period)
    trend_data = []
    daily_totals = db.session.query(
        Expense.date,
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start,
        Expense.date <= end
    )
    
    if category_id:
        daily_totals = daily_totals.filter(Expense.category_id == category_id)
    
    daily_totals = daily_totals.group_by(Expense.date).order_by(Expense.date).all()
    
    for day_data in daily_totals:
        trend_data.append({
            'label': day_data.date.strftime('%m/%d'),
            'amount': float(day_data.total)
        })
    
    # Get top expenses (limit to top 10)
    top_expenses = query.order_by(Expense.amount.desc()).limit(10).all()
    
    # Get budget performance data
    budget_performance = []
    active_budgets = Budget.query.filter(
        Budget.user_id == current_user.id,
        Budget.start_date <= end,
        Budget.end_date >= start
    ).all()
    
    for budget in active_budgets:
        # Calculate spent amount for this budget's category
        spent_query = db.session.query(
            func.sum(Expense.amount).label('spent')
        ).filter(
            Expense.user_id == current_user.id,
            Expense.category_id == budget.category_id,
            Expense.date >= budget.start_date,
            Expense.date <= budget.end_date
        ).first()
        
        spent = spent_query.spent if spent_query.spent else 0
        
        budget_performance.append({
            'category': budget.category,
            'amount': float(budget.amount),
            'spent': float(spent)
        })
    
    # Investment data for the period
    investment_query = Investment.query.filter(
        Investment.user_id == current_user.id,
        Investment.investment_date >= start,
        Investment.investment_date <= end
    )
    
    investments = investment_query.all()
    total_invested = sum([inv.amount for inv in investments])
    total_investment_count = len(investments)
    total_current_value = sum([inv.current_value or inv.amount for inv in investments])
    investment_returns = total_current_value - total_invested
    
    # Investment type breakdown
    investment_type_totals = db.session.query(
        InvestmentType.name,
        InvestmentType.icon,
        func.sum(Investment.amount).label('total'),
        func.sum(Investment.current_value).label('current_value'),
        func.count(Investment.id).label('count')
    ).join(Investment).filter(
        Investment.user_id == current_user.id,
        Investment.investment_date >= start,
        Investment.investment_date <= end
    ).group_by(InvestmentType.id).order_by(
        func.sum(Investment.amount).desc()
    ).all()
    
    # Format investment stats for charts
    investment_stats = []
    for inv_type in investment_type_totals:
        current_val = float(inv_type.current_value) if inv_type.current_value else float(inv_type.total)
        invested_amt = float(inv_type.total)
        returns = current_val - invested_amt
        percentage = (invested_amt / total_invested * 100) if total_invested > 0 else 0
        
        investment_stats.append({
            'name': inv_type.name,
            'icon': inv_type.icon,
            'total': invested_amt,
            'current_value': current_val,
            'returns': returns,
            'count': inv_type.count,
            'percentage': percentage
        })
    
    # Debug: Log the data
    print(f"Debug - Start: {start}, End: {end}")
    print(f"Debug - Total expenses: {total_count}, Total amount: {total_amount}")
    print(f"Debug - Category totals count: {len(category_totals)}")
    print(f"Debug - Payment totals count: {len(payment_totals)}")
    
    return render_template('main/reports.html',
                         title='Reports & Analytics',
                         summary=summary,
                         start_date=start_date,
                         end_date=end_date,
                         total_amount=total_amount,
                         total_count=total_count,
                         category_totals=category_totals,
                         category_stats=category_stats,
                         payment_totals=payment_totals,
                         payment_methods=payment_methods,
                         trend_data=trend_data,
                         top_expenses=top_expenses,
                         budget_performance=budget_performance,
                         categories=categories,
                         selected_category=category_id,
                         total_invested=total_invested,
                         total_investment_count=total_investment_count,
                         total_current_value=total_current_value,
                         investment_returns=investment_returns,
                         investment_stats=investment_stats)

@bp.route('/api/chart_data')
@login_required
def chart_data():
    """API endpoint for chart data"""
    chart_type = request.args.get('type', 'daily')
    
    if chart_type == 'daily':
        # Get daily spending for current month
        today = date.today()
        start_of_month = today.replace(day=1)
        
        daily_data = db.session.query(
            Expense.date,
            func.sum(Expense.amount).label('total')
        ).filter(
            Expense.user_id == current_user.id,
            Expense.date >= start_of_month,
            Expense.date <= today
        ).group_by(Expense.date).order_by(Expense.date).all()
        
        return jsonify({
            'labels': [d.date.strftime('%m/%d') for d in daily_data],
            'data': [float(d.total) for d in daily_data]
        })
    
    elif chart_type == 'category':
        # Get category spending for current month
        today = date.today()
        start_of_month = today.replace(day=1)
        
        category_data = db.session.query(
            Category.name,
            func.sum(Expense.amount).label('total')
        ).join(Expense).filter(
            Expense.user_id == current_user.id,
            Expense.date >= start_of_month,
            Expense.date <= today
        ).group_by(Category.id).order_by(func.sum(Expense.amount).desc()).all()
        
        return jsonify({
            'labels': [d.name for d in category_data],
            'data': [float(d.total) for d in category_data]
        })
    
    return jsonify({'error': 'Invalid chart type'})

# Expense Management Routes
@bp.route('/expenses')
@login_required
def expenses():
    """Redirect to expenses list in expenses blueprint"""
    return redirect(url_for('expenses.list_expenses'))

@bp.route('/edit_expense/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    """Edit an existing expense"""
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = ExpenseForm(obj=expense)
    
    # Populate category choices
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.is_default == True)
    ).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
    # Populate payment method choices
    payment_methods = PaymentMethod.query.filter_by(
        user_id=current_user.id, is_active=True
    ).order_by(PaymentMethod.name).all()
    form.payment_method.choices = [(pm.id, pm.name) for pm in payment_methods]
    
    if form.validate_on_submit():
        expense.title = form.title.data
        expense.amount = form.amount.data
        expense.category_id = form.category_id.data
        expense.description = form.description.data
        expense.date = form.date.data
        expense.payment_method = form.payment_method.data
        
        # Handle remove receipt
        if request.form.get('remove_receipt') == '1':
            if expense.receipt:
                old_file = os.path.join(current_app.config['UPLOAD_FOLDER'], expense.receipt)
                if os.path.exists(old_file):
                    os.remove(old_file)
            expense.receipt = None
        
        # Handle new file upload
        elif form.receipt.data:
            # Remove old receipt if exists
            if expense.receipt:
                old_file = os.path.join(current_app.config['UPLOAD_FOLDER'], expense.receipt)
                if os.path.exists(old_file):
                    os.remove(old_file)
            
            filename = secure_filename(form.receipt.data.filename)
            if filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                form.receipt.data.save(filepath)
                expense.receipt = filename
        
        expense.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('expenses.list_expenses'))
    
    # Get similar expenses for suggestions
    similar_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.category_id == expense.category_id,
        Expense.id != expense.id
    ).order_by(Expense.date.desc()).limit(5).all()
    
    return render_template('main/edit_expense.html', 
                         form=form, 
                         expense=expense,
                         similar_expenses=similar_expenses)

@bp.route('/delete_expense/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    """Delete an expense"""
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Remove receipt file if exists
    if expense.receipt:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], expense.receipt)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('expenses.list_expenses'))

@bp.route('/view_receipt/<int:id>')
@login_required
def view_receipt(id):
    """View expense receipt"""
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if not expense.receipt:
        flash('No receipt found for this expense.', 'error')
        return redirect(url_for('expenses.list_expenses'))
    
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], expense.receipt)

# Category Management Routes - Redirects to expenses blueprint
@bp.route('/categories')
@login_required
def categories():
    """Redirect to expenses categories page"""
    return redirect(url_for('expenses.categories'))

@bp.route('/add_category', methods=['GET', 'POST'])
@login_required
def add_category():
    """Add a new category"""
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data,
            icon=form.icon.data,
            color=form.color.data,
            user_id=current_user.id
        )
        db.session.add(category)
        db.session.commit()
        flash('Category created successfully!', 'success')
        return redirect(url_for('main.categories'))
    
    return render_template('main/add_edit_category.html', form=form, category=None)

@bp.route('/edit_category/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    """Edit a category"""
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.icon = form.icon.data
        category.color = form.color.data
        db.session.commit()
        flash('Category updated successfully!', 'success')
        return redirect(url_for('main.categories'))
    
    return render_template('main/add_edit_category.html', form=form, category=category)

@bp.route('/delete_category/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    """Delete a category"""
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if category.is_default:
        flash('Cannot delete default categories.', 'error')
        return redirect(url_for('main.categories'))
    
    # Move expenses to "Other" category
    other_category = Category.query.filter_by(name='Other', user_id=current_user.id).first()
    if other_category:
        Expense.query.filter_by(category_id=id).update({'category_id': other_category.id})
    
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('main.categories'))

# Budget Management Routes - Redirects to expenses blueprint
@bp.route('/budgets')
@login_required
def budgets():
    """Redirect to expenses budgets page"""
    return redirect(url_for('expenses.budgets'))

@bp.route('/add_budget', methods=['GET', 'POST'])
@login_required
def add_budget():
    """Redirect to expenses add budget page"""
    return redirect(url_for('expenses.add_budget'))

@bp.route('/edit_budget/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_budget(id):
    """Edit a budget"""
    budget = Budget.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = BudgetForm(obj=budget)
    
    # Populate category choices
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.is_default == True)
    ).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        budget.category_id = form.category_id.data
        budget.amount = form.amount.data
        budget.start_date = form.start_date.data
        budget.end_date = form.end_date.data
        budget.description = form.description.data
        db.session.commit()
        flash('Budget updated successfully!', 'success')
        return redirect(url_for('main.budgets'))
    
    return render_template('main/add_edit_budget.html', form=form, budget=budget)

@bp.route('/delete_budget/<int:id>', methods=['POST'])
@login_required
def delete_budget(id):
    """Delete a budget"""
    budget = Budget.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(budget)
    db.session.commit()
    flash('Budget deleted successfully!', 'success')
    return redirect(url_for('main.budgets'))

@bp.route('/search_expenses')
@login_required
def search_expenses():
    """AJAX endpoint for expense search"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        (Expense.title.contains(query)) | (Expense.description.contains(query))
    ).order_by(Expense.date.desc()).limit(10).all()
    
    results = []
    for expense in expenses:
        results.append({
            'id': expense.id,
            'title': expense.title,
            'amount': expense.amount,
            'date': expense.date.strftime('%Y-%m-%d'),
            'category': expense.category.name
        })
    
    return jsonify(results)

@bp.route('/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    form = DeleteAccountForm()
    
    if form.validate_on_submit():
        # Verify confirmation
        confirmation = form.confirmation.data.strip()
        if confirmation != 'DELETE':
            flash(f'Account deletion cancelled. You must type "DELETE" exactly. You entered: "{confirmation}"', 'warning')
            return render_template('main/delete_account_confirm.html', form=form)
        
        try:
            user_id = current_user.id
            
            # Delete all user's investments first (foreign key to investment_type)
            Investment.query.filter_by(user_id=user_id).delete()
            
            # Delete all user's investment types
            InvestmentType.query.filter_by(user_id=user_id).delete()
            
            # Delete all user's expenses
            Expense.query.filter_by(user_id=user_id).delete()
            
            # Delete all user's categories
            Category.query.filter_by(user_id=user_id).delete()
            
            # Delete all user's budgets
            Budget.query.filter_by(user_id=user_id).delete()
            
            # Delete all user's payment methods
            PaymentMethod.query.filter_by(user_id=user_id).delete()
            
            # Delete the user
            user = User.query.get(user_id)
            db.session.delete(user)
            db.session.commit()
            
            flash('Your account and all associated data have been permanently deleted.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting account: {str(e)}', 'danger')
            return redirect(url_for('main.profile'))
    
    return render_template('main/delete_account_confirm.html', form=form)