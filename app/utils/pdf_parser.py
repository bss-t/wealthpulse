"""
PDF Statement Parser
Extracts transaction data from bank/credit card statements
"""
import re
from datetime import datetime
import pdfplumber
from decimal import Decimal

def parse_credit_card_statement(pdf_path, password=None):
    """
    Parse credit card statement and extract transactions.
    Returns list of transactions: [{date, description, amount}, ...]
    
    Args:
        pdf_path: Path to the PDF file
        password: Password for encrypted PDFs (optional)
    """
    transactions = []
    
    try:
        # Open PDF with password if provided
        open_kwargs = {}
        if password:
            open_kwargs['password'] = password
            
        with pdfplumber.open(pdf_path, **open_kwargs) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # Extract transactions from text
                    transactions.extend(extract_transactions_from_text(text))
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        # Try to provide more helpful error message
        if "password" in str(e).lower() or "encrypted" in str(e).lower():
            raise Exception("This PDF is password protected. Please provide the correct password.")
        raise
    
    return transactions

def extract_transactions_from_text(text):
    """
    Extract transaction details from statement text.
    Common patterns:
    - Date Transaction Description Amount
    - DD/MM/YYYY or DD-MM-YYYY or YYYY-MM-DD
    - Amount can be 1,234.56 or 1234.56 or C 1,234.56 (with currency symbol)
    """
    transactions = []
    lines = text.split('\n')
    
    # Pattern to match common transaction formats
    patterns = [
        # Pattern 1: HDFC format - DD/MM/YYYY| HH:MM Description ... C amount.00 l
        r'(\d{2}/\d{2}/\d{4})\|\s*\d{2}:\d{2}\s+(.+?)\s+C\s*([\d,]+\.?\d{0,2})\s*[l|]',
        # Pattern 2: DD/MM/YYYY Description Amount
        r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.?\d{0,2})\s*$',
        # Pattern 3: DD-MMM-YYYY Description Amount
        r'(\d{2}-[A-Z]{3}-\d{4})\s+(.+?)\s+([\d,]+\.?\d{0,2})\s*$',
        # Pattern 4: YYYY-MM-DD Description Amount
        r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.?\d{0,2})\s*$',
        # Pattern 5: DD MMM YYYY Description Amount
        r'(\d{2}\s+[A-Z]{3}\s+\d{4})\s+(.+?)\s+([\d,]+\.?\d{0,2})\s*$',
        # Pattern 6: DD/MM Description Amount (for current year statements)
        r'(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.?\d{0,2})\s*$',
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                description = match.group(2).strip()
                amount_str = match.group(3).replace(',', '')
                
                # Skip lines with keywords that are not transactions
                skip_keywords = ['balance', 'total', 'credit limit', 'minimum due', 
                                'statement', 'page', 'summary', 'opening', 'closing',
                                'previous statement', 'amount due', 'due date',
                                'billing period', 'payment received', 'finance charge']
                if any(keyword in description.lower() for keyword in skip_keywords):
                    continue
                
                # Skip certain transaction types
                if any(skip in description.upper() for skip in ['BPPY CC PAYMENT', 'PAYMENT PP', 'PETRO SURCHARGE WAIVER']):
                    continue
                
                # Parse date
                try:
                    transaction_date = parse_date(date_str)
                    amount = float(amount_str)
                    
                    # Clean up description
                    description = clean_description(description)
                    
                    if transaction_date and amount > 0 and description:
                        transactions.append({
                            'date': transaction_date,
                            'description': description,
                            'amount': amount
                        })
                except (ValueError, Exception) as e:
                    continue
                
                break  # Found a match, move to next line
    
    return transactions

def parse_date(date_str):
    """Parse various date formats"""
    date_formats = [
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y-%m-%d',
        '%d-%b-%Y',
        '%d %b %Y',
        '%d %B %Y',
        '%d/%m',  # DD/MM format (assume current year)
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            # If only month/day, add current year
            if fmt == '%d/%m':
                parsed_date = parsed_date.replace(year=datetime.now().year)
            return parsed_date.date()
        except ValueError:
            continue
    
    return None

def clean_description(description):
    """Clean up transaction description"""
    # Remove extra spaces
    description = re.sub(r'\s+', ' ', description)
    
    # Remove common reference numbers/codes at the end
    description = re.sub(r'\s+\d{10,}$', '', description)
    description = re.sub(r'\s+REF\s*:\s*\w+$', '', description, flags=re.IGNORECASE)
    
    # Remove bonus/rewards indicators (+ followed by numbers)
    description = re.sub(r'\s*\+\s*\d+$', '', description)
    
    # Remove trailing category indicators (l or | at the end)
    description = re.sub(r'\s*[l|]\s*$', '', description)
    
    # Remove "UPI-" prefix
    description = re.sub(r'^UPI-\s*', '', description, flags=re.IGNORECASE)
    
    # Remove location suffixes like "BANGALORE", "BENGALURU", etc.
    description = re.sub(r'\s+(BANGALORE|BENGALURU|GURGOAN|KAR|UR)(\s+[A-Z]{2})?$', '', description, flags=re.IGNORECASE)
    
    # Capitalize properly
    description = description.strip().title()
    
    # Limit length
    if len(description) > 200:
        description = description[:197] + '...'
    
    return description

def extract_transactions_with_ai_fallback(pdf_path, password=None):
    """
    Try standard parsing first, if fails or returns too few transactions,
    use more aggressive text extraction
    
    Args:
        pdf_path: Path to the PDF file
        password: Password for encrypted PDFs (optional)
    """
    transactions = parse_credit_card_statement(pdf_path, password)
    
    # If we got very few transactions, try table extraction
    if len(transactions) < 3:
        open_kwargs = {}
        if password:
            open_kwargs['password'] = password
            
        with pdfplumber.open(pdf_path, **open_kwargs) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    # Try to find date, description, amount columns
                    if table and len(table) > 1:
                        transactions.extend(extract_from_table(table))
    
    return transactions

def extract_from_table(table):
    """Extract transactions from PDF table"""
    transactions = []
    
    # Try to identify header row and column indices
    for row_idx, row in enumerate(table):
        if row_idx == 0:
            # Assume first row is header
            continue
        
        # Look for date-like value in first few columns
        for col_idx, cell in enumerate(row[:3]):
            if cell and isinstance(cell, str):
                date_obj = parse_date(cell.strip())
                if date_obj:
                    # Found date column, extract transaction
                    description = ' '.join([str(c) for c in row[1:] if c and not is_amount(str(c))])
                    amount_str = next((str(c) for c in row if c and is_amount(str(c))), None)
                    
                    if amount_str:
                        try:
                            amount = float(amount_str.replace(',', ''))
                            if amount > 0:
                                transactions.append({
                                    'date': date_obj,
                                    'description': clean_description(description),
                                    'amount': amount
                                })
                        except:
                            pass
                    break
    
    return transactions

def is_amount(text):
    """Check if text looks like a monetary amount"""
    # Remove commas and check if it's a valid number
    text = text.replace(',', '').replace('$', '').strip()
    try:
        float(text)
        return True
    except:
        return False
