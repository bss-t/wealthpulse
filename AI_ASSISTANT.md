# AI Assistant Documentation

## Overview

The WealthPulse AI Assistant is an intelligent chat interface that helps you manage your finances through natural language conversations. Ask questions, get insights, and visualize your spending data without navigating through multiple pages.

## Features

### 📊 Expense Management
- View recent expenses with customizable limits
- Get detailed spending summaries by time period
- Filter expenses by date ranges
- Analyze spending patterns by category

### 💳 Budget Tracking
- Check your current budget status
- See remaining budget for the month
- Get alerts when approaching budget limits
- Track spending against monthly goals

### 💼 Investment Portfolio
- View all your investments
- See current returns and performance
- Track portfolio value over time
- Monitor individual investment performance

### 📈 Data Visualization
Generate beautiful charts and graphs:
- **Pie Charts**: Category-wise spending distribution
- **Timeline Charts**: Daily spending trends over time
- **Bar Charts**: Category comparison with values

### 📁 Category Management
- List all expense categories
- View category descriptions
- Add new categories (coming soon)

## Using the AI Assistant

### Accessing the Assistant
1. Log in to your WealthPulse account
2. Click **"AI Assistant"** in the navigation menu
3. Start chatting!

### Natural Language Understanding

The assistant understands natural language, so you can ask questions conversationally:

#### Viewing Expenses
```
"Show my recent expenses"
"List last 5 expenses"
"What did I spend on last month?"
"Show expenses from December 2025"
```

#### Getting Summaries
```
"What's my spending summary?"
"Summary for December 2025"
"How much did I spend this month?"
"Show spending breakdown for this year"
"Summary from December 1 to December 15"
```

#### Checking Budget
```
"What's my budget status?"
"How much budget do I have left?"
"Am I within budget?"
```

#### Viewing Investments
```
"Show my investments"
"What's my portfolio?"
"How are my investments performing?"
```

#### Generating Charts
```
"Show me a spending chart"
"Show spending timeline for December 2025"
"Show me a pie chart"
"Graph my spending comparison"
"Show chart from December 1-15"
```

### Date Parsing

The assistant understands various date formats:

#### Single Dates
- `"December 25, 2025"` - Specific day
- `"December 2025"` - Entire month
- `"December"` - Current year's December

#### Date Ranges
- `"from December 1 to December 15"`
- `"between Dec 1 and Dec 15, 2025"`
- `"December 1-15"` (shorthand)
- `"from Dec 26 to Dec 28"`

#### Time Periods
- `"this month"` - Current month
- `"this year"` - Current year
- `"all time"` - All expenses

### Chart Types

#### Pie Chart (Category Distribution)
Best for seeing which categories consume most of your budget.

**Commands:**
```
"Show me a spending chart"
"Show pie chart"
"Show category distribution"
```

**Features:**
- Percentage breakdown by category
- Color-coded segments
- Clear labels

#### Timeline Chart (Daily Spending)
Best for identifying spending patterns and trends over time.

**Commands:**
```
"Show spending timeline"
"Show daily spending"
"Show spending over time"
"Graph spending timeline for December"
```

**Features:**
- Line graph with markers
- Date on X-axis
- Amount on Y-axis
- Area fill for visual impact

#### Bar Chart (Category Comparison)
Best for comparing spending across different categories.

**Commands:**
```
"Show spending comparison"
"Show bar chart"
"Compare spending by category"
```

**Features:**
- Horizontal bars for easy reading
- Values displayed on bars
- Sorted by spending (highest to lowest)

### Quick Commands

Use the quick command links below the chat input for instant access:
- **Recent expenses** - Last 10 expenses
- **Summary** - Current month summary
- **Chart** - Category pie chart
- **Budget** - Budget status
- **Help** - Full command list

## Technical Implementation

### Architecture

The AI Assistant is built using:
- **Backend**: Flask (Python)
- **Frontend**: Bootstrap 5 + Vanilla JavaScript
- **Charts**: Matplotlib (server-side rendering)
- **Database**: PostgreSQL

### Components

#### 1. Chat Interface (`app/templates/chat/chat.html`)
- Real-time messaging UI
- Message bubbles for user and assistant
- Image display for charts
- Typing indicators
- Auto-scroll to latest messages

#### 2. Route Handler (`app/chat/routes.py`)
- Message processing and routing
- Natural language parsing
- Date extraction with regex
- Response formatting

#### 3. Assistant Logic (`app/chat/assistant.py`)
- Database queries for expenses, investments
- Summary calculations
- Chart generation with matplotlib
- Base64 image encoding

#### 4. Date Parser
Uses regex patterns to extract:
- Month names (full and abbreviated)
- Day numbers
- Year (4-digit)
- Date ranges with "from...to" or "between...and"
- Hyphenated ranges (e.g., "Dec 1-15")

### Message Flow

1. **User Input** → Chat interface
2. **AJAX Request** → `/chat/message` endpoint
3. **Parse Message** → Extract keywords and dates
4. **Route to Function** → Call appropriate assistant method
5. **Generate Response** → Text or chart image
6. **Return JSON** → `{response: "...", image: "base64..."}`
7. **Display** → Render in chat interface

### Response Types

#### Text Response
```json
{
  "response": "📊 Found 5 expense(s):\n• 2025-12-28...",
  "timestamp": "2026-01-07 12:34:56"
}
```

#### Image Response (Charts)
```json
{
  "response": "",
  "image": "iVBORw0KGgoAAAANSUhEUgAA...",
  "timestamp": "2026-01-07 12:34:56"
}
```

## Keyword Routing

The assistant uses keyword matching to understand intent:

### Expense Keywords
`show expenses`, `list expenses`, `view expenses`, `recent expenses`

### Summary Keywords
`summary`, `total spending`, `how much spent`, `spending breakdown`

### Budget Keywords
`budget`, `remaining`, `left`

### Investment Keywords
`investments`, `portfolio`, `stocks`

### Chart Keywords
`chart`, `graph`, `visualize`, `plot`
- **Type modifiers**: `pie`, `timeline`, `comparison`, `bar`
- **Period modifiers**: `this month`, `this year`, `all time`

### Category Keywords
`categories`, `list categories`, `show categories`

## Customization

### Adding New Commands

1. **Add keyword matching** in `app/chat/routes.py`:
```python
elif any(word in message_lower for word in ['your', 'keywords']):
    return assistant.your_new_method()
```

2. **Implement method** in `app/chat/assistant.py`:
```python
def your_new_method(self):
    # Query database
    # Format response
    return result_string
```

3. **Update help text** to include new command

### Styling

Chat message colors are defined in `app/templates/chat/chat.html`:
- User messages: `#8B0000` (dark red)
- Assistant messages: `#e3f2fd` (light blue)
- Text colors: Automatic contrast adjustment

## Security

### Authentication
- All chat endpoints require login (`@login_required`)
- Each query filters by `current_user.id`
- No cross-user data access

### Input Validation
- Message length validation
- SQL injection prevention through SQLAlchemy ORM
- XSS prevention through HTML escaping

### Data Privacy
- All queries scoped to current user
- No data sharing between users
- Session-based authentication

## Troubleshooting

### Common Issues

**Issue**: Chat not responding
- **Solution**: Check browser console for errors, ensure you're logged in

**Issue**: Charts not displaying
- **Solution**: Ensure matplotlib is installed, check for server errors in logs

**Issue**: Date parsing not working
- **Solution**: Use supported date formats, include year for past dates

**Issue**: Empty responses
- **Solution**: Check if you have data for the requested period

### Debug Mode

Enable debug logging in `app/chat/routes.py`:
```python
print(f"DEBUG - User message: {user_message}")
print(f"DEBUG - Response: {response}")
```

Check Docker logs:
```bash
docker-compose logs web --tail=50
```

## Future Enhancements

### Planned Features
- [ ] Natural language expense creation
- [ ] Budget recommendations based on spending patterns
- [ ] Recurring expense detection
- [ ] Multi-chart comparisons
- [ ] Export conversations
- [ ] Voice input support
- [ ] Integration with OpenAI/Anthropic APIs for smarter responses
- [ ] Conversation history persistence
- [ ] Expense predictions and forecasting

### Integration Ideas
- Email summaries
- SMS notifications for budget alerts
- Calendar integration for expense reminders
- Receipt scanning and OCR

## API Reference

### Chat Endpoint

**POST** `/chat/message`

**Request:**
```json
{
  "message": "Show my expenses from December 2025"
}
```

**Response (Text):**
```json
{
  "response": "📊 Found 5 expense(s):\n• 2025-12-28 - Lunch: INR 70.00\n...",
  "timestamp": "2026-01-07 12:34:56.789012"
}
```

**Response (Image):**
```json
{
  "response": "",
  "image": "base64_encoded_png_data",
  "timestamp": "2026-01-07 12:34:56.789012"
}
```

**Error Response:**
```json
{
  "error": "Error message",
  "timestamp": "2026-01-07 12:34:56.789012"
}
```

## Support

For issues or feature requests, please contact the development team or open an issue in the project repository.

---

**Last Updated**: January 7, 2026  
**Version**: 1.0.0
