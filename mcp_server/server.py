#!/usr/bin/env python3
"""
WealthPulse MCP Server

Provides AI assistants with tools to manage expenses, investments, and financial data.
"""

import os
import sys
from datetime import datetime, date
from pathlib import Path

# Add parent directory to path to import app models
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import User, Expense, Category, Investment, InvestmentType, PaymentMethod, Budget

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/expense_manager')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Initialize MCP server
server = Server("expense-manager")

def get_db():
    """Get database session"""
    return SessionLocal()

def get_user(db, user_id: int):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    return user

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="add_expense",
            description="Add a new expense to WealthPulse",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "title": {"type": "string", "description": "Expense title"},
                    "amount": {"type": "number", "description": "Expense amount"},
                    "category": {"type": "string", "description": "Category name"},
                    "payment_method": {"type": "string", "description": "Payment method name"},
                    "description": {"type": "string", "description": "Optional description"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format (optional, defaults to today)"},
                },
                "required": ["user_id", "title", "amount", "category", "payment_method"],
            },
        ),
        Tool(
            name="list_expenses",
            description="Get a list of expenses with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "limit": {"type": "integer", "description": "Number of expenses to return (default 50)"},
                    "category": {"type": "string", "description": "Filter by category name"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="get_expense_summary",
            description="Get spending summary and statistics for a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "period": {"type": "string", "enum": ["month", "year", "all"], "description": "Time period for summary"},
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="list_categories",
            description="Get all categories for a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="add_category",
            description="Create a new expense category",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "name": {"type": "string", "description": "Category name"},
                    "description": {"type": "string", "description": "Category description (optional)"},
                },
                "required": ["user_id", "name"],
            },
        ),
        Tool(
            name="add_investment",
            description="Add a new investment",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "name": {"type": "string", "description": "Investment name"},
                    "investment_type": {"type": "string", "description": "Investment type name"},
                    "amount": {"type": "number", "description": "Investment amount"},
                    "current_value": {"type": "number", "description": "Current value (optional)"},
                    "date": {"type": "string", "description": "Investment date in YYYY-MM-DD format (optional)"},
                },
                "required": ["user_id", "name", "investment_type", "amount"],
            },
        ),
        Tool(
            name="list_investments",
            description="Get all investments for a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="get_budget_status",
            description="Get current budget status and remaining budget",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                },
                "required": ["user_id"],
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    db = get_db()
    try:
        if name == "add_expense":
            return await add_expense_handler(db, arguments)
        elif name == "list_expenses":
            return await list_expenses_handler(db, arguments)
        elif name == "get_expense_summary":
            return await get_expense_summary_handler(db, arguments)
        elif name == "list_categories":
            return await list_categories_handler(db, arguments)
        elif name == "add_category":
            return await add_category_handler(db, arguments)
        elif name == "add_investment":
            return await add_investment_handler(db, arguments)
        elif name == "list_investments":
            return await list_investments_handler(db, arguments)
        elif name == "get_budget_status":
            return await get_budget_status_handler(db, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    finally:
        db.close()

async def add_expense_handler(db, args):
    """Add a new expense"""
    user = get_user(db, args["user_id"])
    
    # Get or create category
    category = db.query(Category).filter(
        Category.user_id == user.id,
        Category.name == args["category"]
    ).first()
    if not category:
        category = Category(user_id=user.id, name=args["category"])
        db.add(category)
        db.flush()
    
    # Get or create payment method
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == user.id,
        PaymentMethod.name == args["payment_method"]
    ).first()
    if not payment_method:
        payment_method = PaymentMethod(user_id=user.id, name=args["payment_method"])
        db.add(payment_method)
        db.flush()
    
    # Parse date
    expense_date = date.today()
    if "date" in args:
        expense_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
    
    # Create expense
    expense = Expense(
        user_id=user.id,
        title=args["title"],
        amount=args["amount"],
        category_id=category.id,
        payment_method_id=payment_method.id,
        description=args.get("description", ""),
        date=expense_date
    )
    db.add(expense)
    db.commit()
    
    return [TextContent(
        type="text",
        text=f"✅ Expense added successfully!\nID: {expense.id}\nTitle: {expense.title}\nAmount: {user.currency} {expense.amount:.2f}\nCategory: {category.name}\nDate: {expense_date}"
    )]

async def list_expenses_handler(db, args):
    """List expenses with filters"""
    user = get_user(db, args["user_id"])
    
    query = db.query(Expense).filter(Expense.user_id == user.id)
    
    # Apply filters
    if "category" in args:
        category = db.query(Category).filter(
            Category.user_id == user.id,
            Category.name == args["category"]
        ).first()
        if category:
            query = query.filter(Expense.category_id == category.id)
    
    if "start_date" in args:
        start = datetime.strptime(args["start_date"], "%Y-%m-%d").date()
        query = query.filter(Expense.date >= start)
    
    if "end_date" in args:
        end = datetime.strptime(args["end_date"], "%Y-%m-%d").date()
        query = query.filter(Expense.date <= end)
    
    # Get expenses
    limit = args.get("limit", 50)
    expenses = query.order_by(Expense.date.desc()).limit(limit).all()
    
    if not expenses:
        return [TextContent(type="text", text="No expenses found.")]
    
    # Format output
    result = f"📊 Found {len(expenses)} expense(s):\n\n"
    for exp in expenses:
        result += f"• {exp.date} - {exp.title}: {user.currency} {exp.amount:.2f} ({exp.category.name})\n"
    
    total = sum(e.amount for e in expenses)
    result += f"\n💰 Total: {user.currency} {total:.2f}"
    
    return [TextContent(type="text", text=result)]

async def get_expense_summary_handler(db, args):
    """Get spending summary"""
    user = get_user(db, args["user_id"])
    period = args.get("period", "month")
    
    query = db.query(Expense).filter(Expense.user_id == user.id)
    
    # Apply period filter
    today = date.today()
    if period == "month":
        start_date = today.replace(day=1)
        query = query.filter(Expense.date >= start_date)
        period_name = f"{today.strftime('%B %Y')}"
    elif period == "year":
        start_date = today.replace(month=1, day=1)
        query = query.filter(Expense.date >= start_date)
        period_name = str(today.year)
    else:
        period_name = "All Time"
    
    expenses = query.all()
    
    if not expenses:
        return [TextContent(type="text", text=f"No expenses found for {period_name}.")]
    
    # Calculate statistics
    total = sum(e.amount for e in expenses)
    avg = total / len(expenses)
    
    # Category breakdown
    category_totals = {}
    for exp in expenses:
        cat_name = exp.category.name
        category_totals[cat_name] = category_totals.get(cat_name, 0) + exp.amount
    
    # Format output
    result = f"📈 Expense Summary - {period_name}\n\n"
    result += f"Total Spent: {user.currency} {total:.2f}\n"
    result += f"Number of Expenses: {len(expenses)}\n"
    result += f"Average per Expense: {user.currency} {avg:.2f}\n\n"
    result += "By Category:\n"
    for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total) * 100
        result += f"  • {cat}: {user.currency} {amount:.2f} ({percentage:.1f}%)\n"
    
    # Budget comparison
    if user.monthly_budget > 0 and period == "month":
        remaining = user.monthly_budget - total
        percentage_used = (total / user.monthly_budget) * 100
        result += f"\n💳 Budget: {user.currency} {user.monthly_budget:.2f}\n"
        result += f"Remaining: {user.currency} {remaining:.2f} ({percentage_used:.1f}% used)\n"
    
    return [TextContent(type="text", text=result)]

async def list_categories_handler(db, args):
    """List all categories"""
    user = get_user(db, args["user_id"])
    categories = db.query(Category).filter(Category.user_id == user.id).all()
    
    if not categories:
        return [TextContent(type="text", text="No categories found.")]
    
    result = "📁 Categories:\n\n"
    for cat in categories:
        result += f"• {cat.name}"
        if cat.description:
            result += f": {cat.description}"
        result += "\n"
    
    return [TextContent(type="text", text=result)]

async def add_category_handler(db, args):
    """Add a new category"""
    user = get_user(db, args["user_id"])
    
    # Check if category exists
    existing = db.query(Category).filter(
        Category.user_id == user.id,
        Category.name == args["name"]
    ).first()
    
    if existing:
        return [TextContent(type="text", text=f"❌ Category '{args['name']}' already exists.")]
    
    category = Category(
        user_id=user.id,
        name=args["name"],
        description=args.get("description", "")
    )
    db.add(category)
    db.commit()
    
    return [TextContent(type="text", text=f"✅ Category '{category.name}' created successfully!")]

async def add_investment_handler(db, args):
    """Add a new investment"""
    user = get_user(db, args["user_id"])
    
    # Get or create investment type
    inv_type = db.query(InvestmentType).filter(
        InvestmentType.user_id == user.id,
        InvestmentType.name == args["investment_type"]
    ).first()
    if not inv_type:
        inv_type = InvestmentType(user_id=user.id, name=args["investment_type"])
        db.add(inv_type)
        db.flush()
    
    # Parse date
    inv_date = date.today()
    if "date" in args:
        inv_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
    
    # Create investment
    investment = Investment(
        user_id=user.id,
        name=args["name"],
        investment_type_id=inv_type.id,
        amount=args["amount"],
        current_value=args.get("current_value", args["amount"]),
        date=inv_date
    )
    db.add(investment)
    db.commit()
    
    return [TextContent(
        type="text",
        text=f"✅ Investment added successfully!\nName: {investment.name}\nAmount: {user.currency} {investment.amount:.2f}\nType: {inv_type.name}\nDate: {inv_date}"
    )]

async def list_investments_handler(db, args):
    """List all investments"""
    user = get_user(db, args["user_id"])
    investments = db.query(Investment).filter(Investment.user_id == user.id).order_by(Investment.created_at.desc()).all()
    
    if not investments:
        return [TextContent(type="text", text="No investments found.")]
    
    result = "💼 Investments:\n\n"
    total_invested = 0
    total_current = 0
    
    for inv in investments:
        returns = inv.current_value - inv.amount
        returns_pct = (returns / inv.amount) * 100 if inv.amount > 0 else 0
        returns_sign = "📈" if returns >= 0 else "📉"
        
        result += f"• {inv.name} ({inv.investment_type.name})\n"
        result += f"  Invested: {user.currency} {inv.amount:.2f} | Current: {user.currency} {inv.current_value:.2f}\n"
        result += f"  Returns: {returns_sign} {user.currency} {returns:.2f} ({returns_pct:+.2f}%)\n\n"
        
        total_invested += inv.amount
        total_current += inv.current_value
    
    total_returns = total_current - total_invested
    total_returns_pct = (total_returns / total_invested) * 100 if total_invested > 0 else 0
    
    result += f"📊 Total Invested: {user.currency} {total_invested:.2f}\n"
    result += f"💰 Current Value: {user.currency} {total_current:.2f}\n"
    result += f"📈 Total Returns: {user.currency} {total_returns:.2f} ({total_returns_pct:+.2f}%)"
    
    return [TextContent(type="text", text=result)]

async def get_budget_status_handler(db, args):
    """Get budget status"""
    user = get_user(db, args["user_id"])
    
    if user.monthly_budget <= 0:
        return [TextContent(type="text", text="No monthly budget set.")]
    
    # Get current month expenses
    today = date.today()
    start_of_month = today.replace(day=1)
    
    total_spent = db.query(func.sum(Expense.amount)).filter(
        Expense.user_id == user.id,
        Expense.date >= start_of_month,
        Expense.date <= today
    ).scalar() or 0
    
    remaining = user.monthly_budget - total_spent
    percentage_used = (total_spent / user.monthly_budget) * 100
    
    result = f"💳 Budget Status - {today.strftime('%B %Y')}\n\n"
    result += f"Monthly Budget: {user.currency} {user.monthly_budget:.2f}\n"
    result += f"Spent: {user.currency} {total_spent:.2f} ({percentage_used:.1f}%)\n"
    result += f"Remaining: {user.currency} {remaining:.2f}\n\n"
    
    if remaining < 0:
        result += "⚠️ You are over budget!"
    elif percentage_used > 90:
        result += "⚠️ Warning: You've used over 90% of your budget!"
    elif percentage_used > 75:
        result += "⚠️ You've used over 75% of your budget."
    else:
        result += "✅ You're within budget."
    
    return [TextContent(type="text", text=result)]

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
