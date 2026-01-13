# MCP Server for WealthPulse

## Installation

```bash
cd mcp_server
pip install -r requirements.txt
```

## Configuration

Set the database connection string:
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/expense_manager"
```

Make sure your Docker containers are running:
```bash
cd /path/to/expense_manager
docker-compose up -d
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Expense Management
- **add_expense** - Add a new expense with title, amount, category, and payment method
- **list_expenses** - List expenses with optional filters (date range, category, limit)
- **get_expense_summary** - Get spending statistics for month/year/all-time

### Category Management
- **list_categories** - View all expense categories
- **add_category** - Create a new category

### Investment Management
- **add_investment** - Record a new investment
- **list_investments** - View all investments with returns calculation

### Budget Management
- **get_budget_status** - Check budget status and remaining balance

## Integration with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "expense-manager": {
      "command": "python",
      "args": ["/Users/I761607/Documents/code_space/learnhub/randompython/expense_manager/mcp_server/server.py"],
      "env": {
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/expense_manager"
      }
    }
  }
}
```

## Usage Examples

Once connected, you can ask Claude:
- "Add an expense for lunch at 500 rupees in the Food category using Credit Card"
- "Show me my expenses from December 2025"
- "What's my spending summary for 2025?"
- "Add an investment of 10000 in stocks"
- "How much budget do I have left this month?"
- "List all my expense categories"

## Notes

- All tools require a `user_id` parameter
  - To find your user ID, log into the web app and check your profile URL or use: 
    ```bash
    docker-compose exec web python -c "from app.models import User; from app import db, create_app; app = create_app(); \
    with app.app_context(): users = User.query.all(); [print(f'ID: {u.id}, Username: {u.username}') for u in users]"
    ```
- The server shares the same PostgreSQL database as the Flask web application
- Categories and payment methods are created automatically if they don't exist
- Make sure Docker containers are running before using the MCP server
