from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.chat import bp
from app.chat.assistant import ExpenseManagerAssistant
from app.models import ChatMessage
from app import db
import json
import os
import re
from datetime import datetime

@bp.route('/')
@login_required
def chat():
    """Render chat interface with conversation history"""
    # Load recent chat history (last 50 messages)
    messages = ChatMessage.query.filter_by(user_id=current_user.id)\
        .order_by(ChatMessage.created_at.desc())\
        .limit(50)\
        .all()
    messages.reverse()  # Show oldest first
    
    return render_template('chat/chat.html', chat_history=messages)

@bp.route('/message', methods=['POST'])
@login_required
def send_message():
    """Process chat message and return response"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        # Initialize assistant
        assistant = ExpenseManagerAssistant(current_user.id)
        
        # Simple keyword-based routing (you can replace with OpenAI/Anthropic API)
        response = process_message(user_message, assistant)
        
        print(f"DEBUG - User message: {user_message}")
        print(f"DEBUG - Response type: {type(response)}")
        
        # Save to database
        chat_msg = ChatMessage(user_id=current_user.id, message=user_message)
        
        # Handle different response types
        if isinstance(response, dict) and response.get('type') == 'image':
            chat_msg.response = ''
            chat_msg.response_type = 'image'
            chat_msg.image_data = response.get('data')
            db.session.add(chat_msg)
            db.session.commit()
            
            return jsonify({
                'response': '',
                'image': response.get('data'),
                'message_id': chat_msg.id,
                'timestamp': str(datetime.now())
            })
        else:
            print(f"DEBUG - Response: {response[:100] if isinstance(response, str) else 'Not a string'}")
            chat_msg.response = response
            chat_msg.response_type = 'text'
            db.session.add(chat_msg)
            db.session.commit()
            
            return jsonify({
                'response': response,
                'message_id': chat_msg.id,
                'timestamp': str(datetime.now())
            })
    
    except Exception as e:
        print(f"DEBUG - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/history')
@login_required
def get_history():
    """Get chat history for current user"""
    limit = request.args.get('limit', 50, type=int)
    messages = ChatMessage.query.filter_by(user_id=current_user.id)\
        .order_by(ChatMessage.created_at.desc())\
        .limit(limit)\
        .all()
    messages.reverse()
    
    history = []
    for msg in messages:
        history.append({
            'id': msg.id,
            'message': msg.message,
            'response': msg.response,
            'response_type': msg.response_type,
            'image_data': msg.image_data,
            'timestamp': msg.created_at.isoformat()
        })
    
    return jsonify({'history': history})

def parse_date_from_message(message_lower):
    """Extract date range from natural language message"""
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    # Try to match date ranges like "from Dec 1 to Dec 15" or "December 1-15"
    for month_name, month_num in months.items():
        # Pattern: "from Month Day to Month Day" or "between Month Day and Month Day"
        range_pattern = rf'\b(?:from|between)\s+{re.escape(month_name)}\s+(\d{{1,2}})\s+(?:to|and)\s+{re.escape(month_name)}\s+(\d{{1,2}})\b'
        range_match = re.search(range_pattern, message_lower)
        
        if range_match:
            start_day = int(range_match.group(1))
            end_day = int(range_match.group(2))
            
            # Try to find year
            year_match = re.search(r'(20\d{2})', message_lower)
            year = int(year_match.group(1)) if year_match else datetime.now().year
            
            start_date = datetime(year, month_num, start_day).date()
            end_date = datetime(year, month_num, end_day).date()
            return str(start_date), str(end_date)
        
        # Pattern: "Month Day-Day" (e.g., "December 1-15")
        range_pattern2 = rf'\b{re.escape(month_name)}\s+(\d{{1,2}})\s*-\s*(\d{{1,2}})\b'
        range_match2 = re.search(range_pattern2, message_lower)
        
        if range_match2:
            start_day = int(range_match2.group(1))
            end_day = int(range_match2.group(2))
            
            # Try to find year
            year_match = re.search(r'(20\d{2})', message_lower)
            year = int(year_match.group(1)) if year_match else datetime.now().year
            
            start_date = datetime(year, month_num, start_day).date()
            end_date = datetime(year, month_num, end_day).date()
            return str(start_date), str(end_date)
    
    # Try to match "Month Year" or "Month Day" patterns using word boundaries
    for month_name, month_num in months.items():
        # Use word boundary regex to match whole words only
        pattern = r'\b' + re.escape(month_name) + r'\b'
        if re.search(pattern, message_lower):
            # Try to find year
            year_match = re.search(r'(20\d{2})', message_lower)
            year = int(year_match.group(1)) if year_match else datetime.now().year
            
            # Try to find specific day
            day_match = re.search(rf'\b{re.escape(month_name)}\s+(\d{{1,2}})\b', message_lower)
            if day_match:
                day = int(day_match.group(1))
                date_obj = datetime(year, month_num, day).date()
                return str(date_obj), str(date_obj)
            else:
                # Whole month
                from calendar import monthrange
                last_day = monthrange(year, month_num)[1]
                start_date = datetime(year, month_num, 1).date()
                end_date = datetime(year, month_num, last_day).date()
                return str(start_date), str(end_date)
    
    return None, None

def process_message(message, assistant):
    """Process user message and route to appropriate function"""
    message_lower = message.lower()
    
    # Generate charts - check this first before other expense queries
    if any(word in message_lower for word in ['chart', 'graph', 'visualize', 'plot']):
        # Try to parse specific dates from the message
        start_date, end_date = parse_date_from_message(message_lower)
        
        chart_type = 'category'
        
        if 'timeline' in message_lower or 'over time' in message_lower or 'daily' in message_lower:
            chart_type = 'timeline'
        elif 'comparison' in message_lower or 'bar' in message_lower or 'compare' in message_lower:
            chart_type = 'comparison'
        elif 'pie' in message_lower or 'category' in message_lower:
            chart_type = 'category'
        
        if start_date and end_date:
            image_data, error = assistant.generate_spending_chart_for_dates(start_date, end_date, chart_type=chart_type)
        else:
            period = 'month'
            if 'year' in message_lower or 'annual' in message_lower:
                period = 'year'
            elif 'all' in message_lower:
                period = 'all'
            image_data, error = assistant.generate_spending_chart(period=period, chart_type=chart_type)
        
        if error:
            return error
        return {"type": "image", "data": image_data}
    
    # Add expense
    elif any(word in message_lower for word in ['add expense', 'create expense', 'new expense', 'spent', 'bought']):
        return "To add an expense, please provide:\n- Title (what did you buy?)\n- Amount\n- Category (e.g., Food, Transport)\n- Payment method (e.g., Cash, Credit Card)\n\nExample: 'Add expense: Lunch, 250 rupees, Food, Credit Card'"
    
    # List expenses
    elif any(word in message_lower for word in ['show expenses', 'list expenses', 'view expenses', 'recent expenses', 'expenses for']):
        # Check for year-specific query
        year_match = re.search(r'\b(20\d{2})\b', message_lower)
        if year_match:
            year = int(year_match.group(1))
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            return assistant.list_expenses(start_date=start_date, end_date=end_date, limit=1000)
        
        limit = 10
        if 'last 5' in message_lower or '5 expenses' in message_lower:
            limit = 5
        elif 'last 20' in message_lower or '20 expenses' in message_lower:
            limit = 20
        return assistant.list_expenses(limit=limit)
    
    # Expense summary
    elif any(word in message_lower for word in ['summary', 'total spending', 'how much spent', 'spending breakdown']):
        # Try to parse specific dates/months from the message
        start_date, end_date = parse_date_from_message(message_lower)
        
        if start_date and end_date:
            return assistant.get_expense_summary_for_dates(start_date, end_date)
        elif 'year' in message_lower or 'annual' in message_lower:
            return assistant.get_expense_summary(period='year')
        elif 'all' in message_lower or 'total' in message_lower:
            return assistant.get_expense_summary(period='all')
        else:
            return assistant.get_expense_summary(period='month')
    
    # Budget status
    elif any(word in message_lower for word in ['budget', 'remaining', 'left']):
        return assistant.get_budget_status()
    
    # List categories
    elif any(word in message_lower for word in ['categories', 'list categories', 'show categories']):
        return assistant.list_categories()
    
    # List investments
    elif any(word in message_lower for word in ['investments', 'portfolio', 'stocks']):
        return assistant.list_investments()
    
    # Help
    elif any(word in message_lower for word in ['help', 'what can you do', 'commands']):
        return """🤖 I can help you with:

📊 **Expenses**
• "Show my recent expenses"
• "Show me expenses for 2025" (or any year)
• "What's my spending summary this month?"
• "List expenses from last 5 days"

💳 **Budget**
• "How much budget do I have left?"
• "What's my budget status?"

📈 **Charts & Graphs**
• "Show me a spending chart" (pie chart by category)
• "Show spending timeline" (line chart over time)
• "Show spending comparison" (bar chart by category)
• Add "this year" or "this month" to specify period

💼 **Investments**
• "Show my investments"
• "What's my portfolio?"

📁 **Categories**
• "List my categories"
• "Show all categories"

Just ask me anything about your finances!"""
    
    else:
        return f"""I understand you said: "{message}"

I can help you manage your expenses! Try asking:
• "Show my recent expenses"
• "What's my spending summary?"
• "How much budget do I have left?"
• "Show my investments"

Type "help" for more commands."""
