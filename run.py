import os
import sys
from datetime import date
from app import create_app, db
from app.models import User, Category, Expense

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Category': Category, 'Expense': Expense}

def init_db():
    """Initialize the database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if sample user exists
        user = User.query.filter_by(username='demo').first()
        if not user:
            # Create demo user
            user = User(
                username='demo',
                email='user@expense.com',
                first_name='Demo',
                last_name='User',
                currency='USD',
                monthly_budget=2000.0
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            # Create default categories
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
            
            categories = []
            for cat_data in default_categories:
                category = Category(
                    name=cat_data['name'],
                    icon=cat_data['icon'],
                    color=cat_data['color'],
                    user_id=user.id,
                    is_default=True
                )
                db.session.add(category)
                categories.append(category)
            
            db.session.commit()
            
            # Create sample expenses
            from datetime import datetime, timedelta
            sample_expenses = [
                {'title': 'Grocery Shopping', 'amount': 85.50, 'category': 'Food & Dining', 'days_ago': 1},
                {'title': 'Gas Station', 'amount': 45.00, 'category': 'Transportation', 'days_ago': 2},
                {'title': 'Coffee Shop', 'amount': 12.75, 'category': 'Food & Dining', 'days_ago': 3},
                {'title': 'Movie Tickets', 'amount': 28.00, 'category': 'Entertainment', 'days_ago': 5},
                {'title': 'Electric Bill', 'amount': 125.00, 'category': 'Housing & Utilities', 'days_ago': 7},
                {'title': 'Online Course', 'amount': 49.99, 'category': 'Education', 'days_ago': 10},
                {'title': 'Pharmacy', 'amount': 23.45, 'category': 'Healthcare', 'days_ago': 12}
            ]
            
            for exp_data in sample_expenses:
                # Find category by name
                category = next((c for c in categories if c.name == exp_data['category']), categories[0])
                
                expense = Expense(
                    title=exp_data['title'],
                    amount=exp_data['amount'],
                    date=date.today() - timedelta(days=exp_data['days_ago']),
                    category_id=category.id,
                    user_id=user.id,
                    payment_method='debit_card'
                )
                db.session.add(expense)
            
            db.session.commit()
        
        print('Database initialized successfully!')
        print('Default user created:')
        print('  Username/Email: demo or user@expense.com')
        print('  Password: password123')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'init-db':
        init_db()
    else:
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        app.run(host='0.0.0.0', port=port, debug=debug)