from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract

from app.investments import bp
from app.models import Investment, InvestmentType
from app.forms import InvestmentForm, InvestmentTypeForm
from app import db

@bp.route('/')
@login_required
def list_investments():
    # Get all investments for current user
    investments = Investment.query.filter_by(user_id=current_user.id).order_by(Investment.investment_date.desc()).all()
    
    # Calculate totals
    total_invested = sum(inv.amount for inv in investments)
    total_current_value = sum(inv.current_value or inv.amount for inv in investments)
    total_returns = total_current_value - total_invested
    return_percentage = (total_returns / total_invested * 100) if total_invested > 0 else 0
    
    # Group by investment type
    type_summary = db.session.query(
        InvestmentType.name,
        func.sum(Investment.amount).label('total_amount'),
        func.count(Investment.id).label('count')
    ).join(
        Investment, Investment.investment_type_id == InvestmentType.id
    ).filter(
        Investment.user_id == current_user.id
    ).group_by(InvestmentType.name).all()
    
    # Monthly investments
    current_month = date.today().replace(day=1)
    monthly_total = db.session.query(func.sum(Investment.amount)).filter(
        Investment.user_id == current_user.id,
        Investment.investment_date >= current_month
    ).scalar() or 0
    
    return render_template('investments/list_investments.html',
                         title='My Investments',
                         investments=investments,
                         total_invested=total_invested,
                         total_current_value=total_current_value,
                         total_returns=total_returns,
                         return_percentage=return_percentage,
                         type_summary=type_summary,
                         monthly_total=monthly_total)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_investment():
    form = InvestmentForm(user_id=current_user.id)
    
    if form.validate_on_submit():
        investment = Investment(
            name=form.name.data,
            investment_type_id=form.investment_type_id.data,
            amount=form.amount.data,
            investment_date=form.investment_date.data,
            expected_return=form.expected_return.data,
            maturity_date=form.maturity_date.data,
            current_value=form.current_value.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        
        db.session.add(investment)
        db.session.commit()
        
        flash(f'Investment "{investment.name}" added successfully!', 'success')
        return redirect(url_for('investments.list_investments'))
    
    return render_template('investments/add_investment.html',
                         title='Add Investment',
                         form=form)

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_investment(id):
    investment = Investment.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = InvestmentForm(user_id=current_user.id)
    
    if form.validate_on_submit():
        investment.name = form.name.data
        investment.investment_type_id = form.investment_type_id.data
        investment.amount = form.amount.data
        investment.investment_date = form.investment_date.data
        investment.expected_return = form.expected_return.data
        investment.maturity_date = form.maturity_date.data
        investment.current_value = form.current_value.data
        investment.notes = form.notes.data
        investment.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Investment "{investment.name}" updated successfully!', 'success')
        return redirect(url_for('investments.list_investments'))
    
    elif request.method == 'GET':
        form.name.data = investment.name
        form.investment_type_id.data = investment.investment_type_id
        form.amount.data = investment.amount
        form.investment_date.data = investment.investment_date
        form.expected_return.data = investment.expected_return
        form.maturity_date.data = investment.maturity_date
        form.current_value.data = investment.current_value
        form.notes.data = investment.notes
    
    return render_template('investments/edit_investment.html',
                         title='Edit Investment',
                         form=form,
                         investment=investment)

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_investment(id):
    investment = Investment.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name = investment.name
    
    db.session.delete(investment)
    db.session.commit()
    
    flash(f'Investment "{name}" deleted successfully!', 'success')
    return redirect(url_for('investments.list_investments'))

# Investment Type Management Routes
@bp.route('/types')
@login_required
def investment_types():
    types = InvestmentType.query.filter(
        (InvestmentType.user_id == current_user.id) | (InvestmentType.user_id == None),
        InvestmentType.is_active == True
    ).order_by(InvestmentType.name).all()
    
    return render_template('investments/investment_types.html',
                         title='Investment Types',
                         types=types)

@bp.route('/types/add', methods=['GET', 'POST'])
@login_required
def add_investment_type():
    form = InvestmentTypeForm()
    
    if form.validate_on_submit():
        investment_type = InvestmentType(
            name=form.name.data,
            description=form.description.data,
            icon=form.icon.data,
            user_id=current_user.id
        )
        
        db.session.add(investment_type)
        db.session.commit()
        
        flash(f'Investment type "{investment_type.name}" added successfully!', 'success')
        return redirect(url_for('investments.investment_types'))
    
    return render_template('investments/add_investment_type.html',
                         title='Add Investment Type',
                         form=form)

@bp.route('/types/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_investment_type(id):
    investment_type = InvestmentType.query.filter(
        InvestmentType.id == id,
        (InvestmentType.user_id == current_user.id) | (InvestmentType.user_id == None)
    ).first_or_404()
    
    # If it's a default type, prevent editing
    if investment_type.is_default:
        flash('Cannot edit system default investment types.', 'error')
        return redirect(url_for('investments.investment_types'))
    
    form = InvestmentTypeForm()
    
    if form.validate_on_submit():
        investment_type.name = form.name.data
        investment_type.description = form.description.data
        investment_type.icon = form.icon.data
        
        db.session.commit()
        flash(f'Investment type "{investment_type.name}" updated successfully!', 'success')
        return redirect(url_for('investments.investment_types'))
    
    elif request.method == 'GET':
        form.name.data = investment_type.name
        form.description.data = investment_type.description
        form.icon.data = investment_type.icon
    
    return render_template('investments/edit_investment_type.html',
                         title='Edit Investment Type',
                         form=form,
                         investment_type=investment_type)

@bp.route('/types/delete/<int:id>', methods=['POST'])
@login_required
def delete_investment_type(id):
    investment_type = InvestmentType.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Check if there are investments using this type
    investment_count = Investment.query.filter_by(investment_type_id=id, user_id=current_user.id).count()
    
    if investment_count > 0:
        flash(f'Cannot delete investment type "{investment_type.name}" because it is being used by {investment_count} investment(s).', 'error')
        return redirect(url_for('investments.investment_types'))
    
    # Soft delete
    investment_type.is_active = False
    db.session.commit()
    
    flash(f'Investment type "{investment_type.name}" deleted successfully!', 'success')
    return redirect(url_for('investments.investment_types'))

