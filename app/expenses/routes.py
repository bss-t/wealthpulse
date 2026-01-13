from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, extract
import os
import uuid

from app.expenses import bp
from app.models import Expense, Category, Budget, PaymentMethod
from app.forms import ExpenseForm, CategoryForm, BudgetForm
from app import db
from app.utils.expense_classifier import ExpenseClassifier, DuplicateDetector

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    form = ExpenseForm(user_id=current_user.id)
    
    if form.validate_on_submit():
        # Check for duplicates
        duplicate_detector = DuplicateDetector(current_user.id, db.session)
        is_dup, existing = duplicate_detector.is_duplicate(
            form.title.data,
            form.amount.data,
            form.date.data
        )
        
        if is_dup:
            flash(f'⚠️ Potential duplicate detected! An expense "{existing.title}" '
                  f'with amount {existing.amount} on {existing.date} already exists.', 'warning')
            # Still allow adding, but warn the user
        
        # Auto-classify if no category selected or "Other" selected
        category_id = form.category_id.data
        classification_method = None
        
        if not category_id or category_id == get_other_category_id():
            classifier = ExpenseClassifier(current_user.id, db.session)
            suggested_category, method = classifier.classify(
                form.title.data,
                form.description.data if form.description.data else None
            )
            if suggested_category:
                category_id = suggested_category
                classification_method = method
                category_name = classifier.get_category_name(category_id)
                if method == 'ml':
                    flash(f'🤖 ML auto-classified as "{category_name}"', 'info')
                else:
                    flash(f'💡 Auto-classified as "{category_name}"', 'info')
        
        expense = Expense(
            title=form.title.data,
            description=form.description.data,
            amount=form.amount.data,
            date=form.date.data,
            category_id=category_id,
            payment_method_id=form.payment_method.data,
            user_id=current_user.id
        )
        
        # Handle file upload
        if form.receipt.data:
            filename = save_receipt_file(form.receipt.data)
            if filename:
                expense.receipt_filename = filename
        
        db.session.add(expense)
        db.session.commit()
        
        # Check if model should be retrained (continuous learning)
        classifier = ExpenseClassifier(current_user.id, db.session)
        if classifier.should_retrain():
            result = classifier.retrain_model()
            if result.get('success'):
                flash(f'🎓 ML model updated with new data!', 'info')
        
        flash(f'Expense "{expense.title}" added successfully!', 'success')
        return redirect(url_for('expenses.list_expenses'))
    
    return render_template('expenses/add_expense.html', title='Add Expense', form=form)

@bp.route('/list')
@login_required
def list_expenses():
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    search = request.args.get('search', type=str)
    sort_by = request.args.get('sort_by', 'date', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    
    # Base query
    query = Expense.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= start)
        except ValueError:
            flash('Invalid start date format', 'danger')
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= end)
        except ValueError:
            flash('Invalid end date format', 'danger')
    
    if search:
        query = query.filter(
            (Expense.title.contains(search)) | 
            (Expense.description.contains(search))
        )
    
    # Apply sorting
    sort_column = {
        'date': Expense.date,
        'title': Expense.title,
        'amount': Expense.amount,
        'category': Category.name,
        'payment_method': Expense.payment_method
    }.get(sort_by, Expense.date)
    
    if sort_by == 'category':
        query = query.join(Category)
    
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Paginate results
    expenses = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate monthly total for current month
    today = datetime.now().date()
    start_of_month = today.replace(day=1)
    start_of_week = today - timedelta(days=today.weekday())
    
    monthly_total = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_of_month
    ).with_entities(func.sum(Expense.amount)).scalar() or 0
    
    weekly_total = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_of_week
    ).with_entities(func.sum(Expense.amount)).scalar() or 0
    
    # Calculate average expense
    total_expenses = Expense.query.filter_by(user_id=current_user.id).count()
    total_amount = Expense.query.filter_by(user_id=current_user.id).with_entities(func.sum(Expense.amount)).scalar() or 0
    avg_expense = total_amount / total_expenses if total_expenses > 0 else 0
    
    # Get categories for filter
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    
    return render_template('expenses/list_expenses.html',
                         title='My Expenses',
                         expenses=expenses,
                         categories=categories,
                         monthly_total=monthly_total,
                         weekly_total=weekly_total,
                         total_expenses=total_expenses,
                         avg_expense=avg_expense,
                         sort_by=sort_by,
                         sort_order=sort_order)

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = ExpenseForm(user_id=current_user.id)
    
    if form.validate_on_submit():
        expense.title = form.title.data
        expense.description = form.description.data
        expense.amount = form.amount.data
        expense.date = form.date.data
        expense.category_id = form.category_id.data
        expense.payment_method = form.payment_method.data
        
        # Handle file upload
        if form.receipt.data:
            # Delete old file if exists
            if expense.receipt_filename:
                old_file = os.path.join(current_app.config['UPLOAD_FOLDER'], expense.receipt_filename)
                if os.path.exists(old_file):
                    os.remove(old_file)
            
            filename = save_receipt_file(form.receipt.data)
            if filename:
                expense.receipt_filename = filename
        
        db.session.commit()
        flash(f'Expense "{expense.title}" updated successfully!', 'success')
        return redirect(url_for('expenses.list_expenses'))
    
    elif request.method == 'GET':
        form.title.data = expense.title
        form.description.data = expense.description
        form.amount.data = expense.amount
        form.date.data = expense.date
        form.category_id.data = expense.category_id
        form.payment_method.data = expense.payment_method
    
    return render_template('expenses/edit_expense.html', 
                         title='Edit Expense', 
                         form=form, 
                         expense=expense)

@bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_expense(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Delete receipt file if exists
    if expense.receipt_filename:
        receipt_file = os.path.join(current_app.config['UPLOAD_FOLDER'], expense.receipt_filename)
        if os.path.exists(receipt_file):
            os.remove(receipt_file)
    
    db.session.delete(expense)
    db.session.commit()
    
    flash(f'Expense "{expense.title}" deleted successfully!', 'success')
    return redirect(url_for('expenses.list_expenses'))

@bp.route('/categories')
@login_required
def categories():
    from sqlalchemy import func, and_
    from datetime import datetime, date
    
    # Get categories with spending data (include both user and default categories)
    categories_query = db.session.query(
        Category,
        func.coalesce(func.sum(Expense.amount), 0).label('total_spent'),
        func.count(Expense.id).label('expense_count')
    ).outerjoin(Expense, and_(
        Expense.category_id == Category.id,
        Expense.user_id == current_user.id
    )).filter(
        (Category.user_id == current_user.id) | (Category.is_default == True),
        Category.is_active == True
    ).group_by(Category.id).order_by(Category.name)
    
    user_categories = []
    for category, total_spent, expense_count in categories_query.all():
        # Add calculated attributes to category object
        category.total_spent = float(total_spent or 0)
        category.expense_count = int(expense_count or 0)
        category.current_budget = None  # For now, we'll add budget logic later if needed
        user_categories.append(category)
    
    # Get top categories for sidebar
    top_categories = [cat for cat in user_categories if cat.total_spent > 0]
    top_categories.sort(key=lambda x: x.total_spent, reverse=True)
    top_categories = top_categories[:5]
    
    return render_template('expenses/categories.html', 
                         title='Manage Categories', 
                         categories=user_categories,
                         top_categories=top_categories)

@bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            icon=form.icon.data,
            color=form.color.data,
            user_id=current_user.id
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash(f'Category "{category.name}" created successfully!', 'success')
        return redirect(url_for('expenses.categories'))
    
    return render_template('expenses/add_category.html', title='Add Category', form=form)

@bp.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    # Allow editing of user's own categories or default categories
    category = Category.query.filter(
        Category.id == id,
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).first_or_404()
    
    # If it's a default category, prevent editing
    if category.is_default:
        flash('Cannot edit system default categories.', 'error')
        return redirect(url_for('expenses.categories'))
    
    form = CategoryForm()
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.icon = form.icon.data
        category.color = form.color.data
        
        db.session.commit()
        flash(f'Category "{category.name}" updated successfully!', 'success')
        return redirect(url_for('expenses.categories'))
    
    elif request.method == 'GET':
        form.name.data = category.name
        form.icon.data = category.icon
        form.color.data = category.color
    
    return render_template('expenses/edit_category.html', 
                         title='Edit Category', 
                         form=form, 
                         category=category)

@bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    category.is_active = False
    db.session.commit()
    flash(f'Category "{category.name}" deleted successfully!', 'success')
    return redirect(url_for('expenses.categories'))

@bp.route('/budgets')
@login_required
def budgets():
    # Get current budgets (active ones that include today's date)
    today = date.today()
    current_budgets = Budget.query.filter(
        Budget.user_id == current_user.id,
        Budget.start_date <= today,
        Budget.end_date >= today
    ).all()
    
    return render_template('expenses/budgets.html', 
                         title='Budget Management', 
                         budgets=current_budgets,
                         current_month=today.strftime('%B %Y'))

@bp.route('/budgets/add', methods=['GET', 'POST'])
@login_required
def add_budget():
    form = BudgetForm(user_id=current_user.id)
    
    if form.validate_on_submit():
        # Check if budget already exists for this category and date range
        existing_budget = Budget.query.filter_by(
            category_id=form.category_id.data,
            user_id=current_user.id,
            start_date=form.start_date.data,
            end_date=form.end_date.data
        ).first()
        
        if existing_budget:
            flash('Budget already exists for this category and date range. Please edit the existing budget.', 'warning')
            return redirect(url_for('expenses.budgets'))
        
        budget = Budget(
            category_id=form.category_id.data,
            user_id=current_user.id,
            amount=form.amount.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data
        )
        
        db.session.add(budget)
        db.session.commit()
        
        flash(f'Budget created successfully!', 'success')
        return redirect(url_for('expenses.budgets'))
    
    return render_template('expenses/add_budget.html', title='Add Budget', form=form)

@bp.route('/budgets/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_budget(id):
    budget = Budget.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = BudgetForm(obj=budget)
    
    # Populate category choices
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id).all()]
    
    if form.validate_on_submit():
        budget.category_id = form.category_id.data
        budget.amount = form.amount.data
        budget.start_date = form.start_date.data
        budget.end_date = form.end_date.data
        
        db.session.commit()
        flash('Budget updated successfully!', 'success')
        return redirect(url_for('expenses.budgets'))
    
    return render_template('expenses/add_budget.html', title='Edit Budget', form=form, budget=budget)

@bp.route('/budgets/delete/<int:id>', methods=['POST'])
@login_required
def delete_budget(id):
    budget = Budget.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(budget)
    db.session.commit()
    flash('Budget deleted successfully!', 'success')
    return redirect(url_for('expenses.budgets'))

@bp.route('/payment-methods')
@login_required
def payment_methods():
    methods = PaymentMethod.query.filter_by(user_id=current_user.id, is_active=True).order_by(PaymentMethod.name).all()
    return render_template('expenses/payment_methods.html', title='Payment Methods', methods=methods)

@bp.route('/payment-methods/add', methods=['GET', 'POST'])
@login_required
def add_payment_method():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        icon = request.form.get('icon', 'fas fa-credit-card')
        
        method = PaymentMethod(
            name=name,
            description=description,
            icon=icon,
            user_id=current_user.id
        )
        
        db.session.add(method)
        db.session.commit()
        
        flash('Payment method added successfully!', 'success')
        return redirect(url_for('expenses.payment_methods'))
    
    return render_template('expenses/add_payment_method.html', title='Add Payment Method')

@bp.route('/payment-methods/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_payment_method(id):
    method = PaymentMethod.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        method.name = request.form.get('name')
        method.description = request.form.get('description')
        method.icon = request.form.get('icon', 'fas fa-credit-card')
        
        db.session.commit()
        flash('Payment method updated successfully!', 'success')
        return redirect(url_for('expenses.payment_methods'))
    
    return render_template('expenses/add_payment_method.html', title='Edit Payment Method', method=method)

@bp.route('/payment-methods/delete/<int:id>', methods=['POST'])
@login_required
def delete_payment_method(id):
    method = PaymentMethod.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    method.is_active = False
    db.session.commit()
    flash('Payment method deleted successfully!', 'success')
    return redirect(url_for('expenses.payment_methods'))

@bp.route('/receipt/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

def get_other_category_id():
    """Get the 'Other' category ID"""
    other_cat = Category.query.filter_by(name='Other', is_active=True).first()
    return other_cat.id if other_cat else None

def save_receipt_file(file):
    """Save uploaded receipt file and return filename"""
    if file:
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            return unique_filename
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'danger')
            return None
    return None

@bp.route('/upload_statement', methods=['GET', 'POST'])
@login_required
def upload_statement():
    from app.forms import StatementUploadForm
    from app.utils.pdf_parser import extract_transactions_with_ai_fallback
    
    form = StatementUploadForm()
    
    # Populate category and payment method choices
    form.default_category_id.choices = [
        (c.id, c.name) for c in Category.query.filter(
            (Category.user_id == current_user.id) | (Category.user_id == None),
            Category.is_active == True
        ).order_by(Category.name).all()
    ]
    
    form.default_payment_method.choices = [
        (pm.id, pm.name) for pm in PaymentMethod.query.filter(
            (PaymentMethod.user_id == current_user.id) | (PaymentMethod.user_id == None),
            PaymentMethod.is_active == True
        ).order_by(PaymentMethod.name).all()
    ]
    
    if form.validate_on_submit():
        file = form.statement_file.data
        if file:
            # Save the PDF temporarily
            filename = secure_filename(file.filename)
            temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4().hex}_{filename}")
            file.save(temp_path)
            
            try:
                # Parse the statement
                password = form.pdf_password.data if form.pdf_password.data else None
                transactions = extract_transactions_with_ai_fallback(temp_path, password)
                
                if not transactions:
                    flash('No transactions found in the statement. Please check the file format.', 'warning')
                    os.remove(temp_path)
                    return redirect(url_for('expenses.upload_statement'))
                
                # Initialize classifier and duplicate detector
                classifier = ExpenseClassifier(current_user.id, db.session)
                duplicate_detector = DuplicateDetector(current_user.id, db.session)
                
                # Add transactions as expenses
                added_count = 0
                duplicate_count = 0
                auto_classified_count = 0
                ml_classified_count = 0
                
                for trans in transactions:
                    title = trans['description'][:200]  # Limit to 200 chars
                    
                    # Check for duplicates using enhanced duplicate detector
                    is_dup, existing = duplicate_detector.is_duplicate(
                        title,
                        trans['amount'],
                        trans['date'],
                        threshold=0.80  # 80% similarity threshold
                    )
                    
                    if is_dup:
                        duplicate_count += 1
                        continue
                    
                    # Auto-classify the expense (CSV has title only)
                    category_id, method = classifier.classify(title, None)
                    if category_id:
                        auto_classified_count += 1
                        if method == 'ml':
                            ml_classified_count += 1
                    else:
                        category_id = form.default_category_id.data
                    
                    # Create expense
                    expense = Expense(
                        title=title,
                        description=f"Imported from statement: {filename}",
                        amount=trans['amount'],
                        date=trans['date'],
                        category_id=category_id,
                        payment_method_id=form.default_payment_method.data,
                        user_id=current_user.id
                    )
                    db.session.add(expense)
                    added_count += 1
                
                db.session.commit()
                
                # Retrain ML model with new data (continuous learning)
                if added_count > 0 and classifier.should_retrain():
                    result = classifier.retrain_model()
                    if result.get('success'):
                        print(f"🎓 ML model retrained after import")
                
                # Clean up temp file
                os.remove(temp_path)
                
                # Show result
                if added_count > 0:
                    flash(f'✅ Successfully imported {added_count} transactions!', 'success')
                    if ml_classified_count > 0:
                        flash(f'🤖 {ml_classified_count} transactions classified by ML', 'info')
                    elif auto_classified_count > 0:
                        flash(f'💡 {auto_classified_count} transactions auto-classified', 'info')
                    if duplicate_count > 0:
                        flash(f'⚠️ {duplicate_count} duplicates were skipped.', 'info')
                else:
                    flash('No new transactions were added (all were duplicates).', 'warning')
                
                return redirect(url_for('expenses.list_expenses'))
                
            except Exception as e:
                flash(f'Error parsing statement: {str(e)}', 'danger')
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return redirect(url_for('expenses.upload_statement'))
    
    return render_template('expenses/upload_statement.html', 
                         title='Upload Bank Statement', 
                         form=form)

@bp.route('/duplicates')
@login_required
def find_duplicates():
    """Find and display potential duplicate expenses"""
    duplicate_detector = DuplicateDetector(current_user.id, db.session)
    duplicates = duplicate_detector.find_all_duplicates(limit=200)
    
    return render_template('expenses/duplicates.html',
                         title='Duplicate Expenses',
                         duplicates=duplicates)

@bp.route('/duplicates/merge', methods=['POST'])
@login_required
def merge_duplicates():
    """Merge duplicate expenses"""
    keep_id = request.form.get('keep_id', type=int)
    delete_id = request.form.get('delete_id', type=int)
    
    if not keep_id or not delete_id:
        flash('Invalid request', 'danger')
        return redirect(url_for('expenses.find_duplicates'))
    
    duplicate_detector = DuplicateDetector(current_user.id, db.session)
    success = duplicate_detector.merge_duplicates(keep_id, delete_id)
    
    if success:
        flash('Duplicate expense removed successfully!', 'success')
    else:
        flash('Error removing duplicate', 'danger')
    
    return redirect(url_for('expenses.find_duplicates'))

@bp.route('/ml-stats')
@login_required
def ml_stats():
    """View ML model statistics and training status"""
    try:
        classifier = ExpenseClassifier(current_user.id, db.session)
        
        stats = {
            'ml_available': classifier.use_ml,
            'last_trained': classifier.ml_classifier.last_trained if classifier.ml_classifier else None,
            'training_size': classifier.ml_classifier.training_size if classifier.ml_classifier else 0,
            'needs_retraining': classifier.should_retrain() if classifier.use_ml else False,
            'total_expenses': Expense.query.filter_by(user_id=current_user.id).count()
        }
        
        # Get category distribution
        from sqlalchemy import func
        category_dist = db.session.query(
            Category.name, func.count(Expense.id)
        ).join(Expense).filter(
            Expense.user_id == current_user.id
        ).group_by(Category.name).all()
        
        stats['category_distribution'] = {name: count for name, count in category_dist}
        
        return render_template('expenses/ml_stats.html',
                             title='ML Statistics',
                             stats=stats)
    except Exception as e:
        flash(f'Error loading ML stats: {str(e)}', 'danger')
        return redirect(url_for('expenses.list_expenses'))

@bp.route('/train-ml', methods=['POST'])
@login_required
def train_ml():
    """Manually trigger ML model training"""
    try:
        classifier = ExpenseClassifier(current_user.id, db.session)
        result = classifier.retrain_model()
        
        if result.get('success'):
            accuracy = result.get('accuracy', 0)
            sample_count = result.get('sample_count', 0)
            flash(f'🎓 ML model trained successfully! '
                  f'Samples: {sample_count}, Accuracy: {accuracy*100:.1f}%', 'success')
        else:
            flash(f'⚠️ Training failed: {result.get("message", "Unknown error")}', 'warning')
    except Exception as e:
        flash(f'Error training model: {str(e)}', 'danger')
    
    return redirect(url_for('expenses.ml_stats'))

@bp.route('/view_receipt/<int:id>')
@login_required
def view_receipt(id):
    """View receipt file for an expense"""
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if not expense.receipt:
        flash('No receipt found for this expense.', 'error')
        return redirect(url_for('expenses.list'))
    
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], expense.receipt)

@bp.route('/api/predict-category', methods=['POST'])
@login_required
def predict_category():
    """
    API endpoint for real-time category prediction
    Returns predicted category ID and confidence
    """
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text or len(text) < 3:
        return jsonify({
            'success': False,
            'message': 'Text too short'
        })
    
    try:
        classifier = ExpenseClassifier(current_user.id, db.session)
        # For real-time prediction, we only have title (description not yet entered)
        result = classifier.classify(text, None)
        print(f"Classification result: {result}, type: {type(result)}")
        
        # Unpack the result
        if isinstance(result, tuple) and len(result) == 2:
            category_id, method = result
        else:
            print(f"Unexpected result format: {result}")
            return jsonify({
                'success': False,
                'message': 'Invalid classification result'
            })
        
        print(f"Category ID: {category_id}, type: {type(category_id)}")
        print(f"Method: {method}, type: {type(method)}")
        
        if category_id:
            # Get category details
            category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
            
            if not category:
                return jsonify({
                    'success': False,
                    'message': f'Category {category_id} not found'
                })
            
            confidence = 0.0
            
            # Get confidence score if ML was used
            if method == 'ml' and classifier.use_ml and classifier.ml_classifier:
                try:
                    confidence = classifier.ml_classifier.get_confidence(text)
                except Exception as conf_error:
                    print(f"Error getting confidence: {conf_error}")
                    confidence = 0.0
            
            return jsonify({
                'success': True,
                'category_id': category_id,
                'category_name': category.name if category else 'Unknown',
                'method': method,
                'confidence': round(confidence * 100, 1),
                'icon': category.icon if category else 'fas fa-tag',
                'color': category.color if category else 'secondary'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not predict category'
            })
            
    except Exception as e:
        import traceback
        print(f"Error in predict_category: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500