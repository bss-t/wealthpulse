#!/bin/bash

# Test script for MCP server

echo "Testing MCP Server..."
echo ""

# Test with user_id 1 (adjust as needed)
USER_ID=1

echo "1. Testing list_categories..."
python server.py <<EOF
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_categories","arguments":{"user_id":$USER_ID}}}
EOF

echo ""
echo "2. Testing get_expense_summary..."
python server.py <<EOF
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_expense_summary","arguments":{"user_id":$USER_ID,"period":"month"}}}
EOF

echo ""
echo "3. Testing list_expenses..."
python server.py <<EOF
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_expenses","arguments":{"user_id":$USER_ID,"limit":5}}}
EOF

echo ""
echo "Done!"
