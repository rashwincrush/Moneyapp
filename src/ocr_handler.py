import pytesseract
from PIL import Image
import re
from datetime import datetime
from dateutil import parser
import io

class OCRHandler:
    @staticmethod
    def process_image(image_bytes):
        # Convert bytes to image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Extract text from image
        text = pytesseract.image_to_string(image)
        
        # More precise Rupee symbol handling
        text = re.sub(r'(?:Rs\.?|INR|\bRs\b)\s*', '₹', text, flags=re.IGNORECASE)
        text = re.sub(r'(?<![0-9])2(?=\s*[0-9])', '₹', text)
        text = re.sub(r'₹\s*₹', '₹', text)
        
        return text

    @staticmethod
    def extract_date(text):
        """Extract date from text using various patterns."""
        # Common date patterns
        date_patterns = [
            # DD Month YYYY
            r'(\d{1,2})\s*(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*(?:\d{2,4})?',
            # DD-MM-YYYY or DD/MM/YYYY
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})',
            # YYYY-MM-DD
            r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
            # Month DD, YYYY
            r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*(\d{1,2})(?:\s*,\s*|\s+)(\d{4})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # Try to parse the matched date
                    date_str = match.group(0)
                    parsed_date = parser.parse(date_str)
                    return parsed_date.strftime('%Y-%m-%d')
                except:
                    continue

        return None

    @staticmethod
    def is_failed_transaction(text):
        """Check if the transaction text indicates a failed transaction."""
        failed_indicators = [
            'failed', 'failure', 'declined', 'rejected', 'unsuccessful',
            'transaction failed', 'payment failed', 'not successful',
            'could not process', 'error', 'invalid'
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in failed_indicators)

    @staticmethod
    def create_transaction_key(transaction):
        """Create a unique key for a transaction to detect duplicates."""
        return f"{transaction['date']}_{transaction['amount']}_{transaction['type']}"

    @staticmethod
    def extract_transactions(text):
        """
        Extract all transactions from the text.
        
        Returns:
            list: List of transaction dictionaries, each containing:
                - amount: float
                - type: 'credit' or 'debit'
                - description: str
                - date: str (YYYY-MM-DD)
        """
        transactions = []
        seen_transactions = set()  # For detecting duplicates
        
        # Split text into lines
        lines = text.split('\n')
        
        # Amount pattern with optional '+' or '-' sign
        amount_pattern = r'₹\s*(\d+(?:,\d+)*(?:\.\d{2})?)'
        
        # Common patterns for transaction descriptions
        description_patterns = [
            # Standard patterns
            r'(?:from|to|paid to|received from)\s+([A-Za-z0-9\s\-\.]+?)(?=\s+(?:on|at|via|₹|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)))',
            r'(?:UPI|IMPS|NEFT|RTGS)\s*[-:]?\s*([A-Za-z0-9\s\-\.]+)',
            r'([A-Za-z0-9\s\-\.]+?)(?=\s+(?:paid|sent|received))',
            # Additional patterns for common transaction formats
            r'([A-Za-z0-9\s\-\.]+?)\s+(?:UPI|IMPS|NEFT|RTGS)',
            r'(?:payment|transfer)\s+(?:to|from)\s+([A-Za-z0-9\s\-\.]+)',
            # Catch-all pattern for any word sequence before amount
            r'([A-Za-z0-9\s\-\.]{3,}?)(?=\s*₹)'
        ]
        
        current_date = None
        
        # Process each line
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip header-like lines
            if any(header in line.lower() for header in ['search transaction', 'status', 'payment method']):
                continue
            
            # Skip failed transactions
            if OCRHandler.is_failed_transaction(line):
                continue
            
            # Try to extract date from the line
            line_date = OCRHandler.extract_date(line)
            if line_date:
                current_date = line_date
                continue
            
            # Find amount in the line
            amount_match = re.search(amount_pattern, line)
            if not amount_match:
                continue
                
            # Initialize transaction
            transaction = {
                'amount': 0.0,
                'type': 'debit',  # default to debit
                'description': '',
                'date': current_date or datetime.now().strftime('%Y-%m-%d'),  # fallback to current date if no date found
                'category': 'Other'  # Default category
            }
            
            # Extract amount
            amount_str = amount_match.group(1).replace(',', '')
            transaction['amount'] = float(amount_str)
            
            # Try to find date in the same line
            line_date = OCRHandler.extract_date(line)
            if line_date:
                transaction['date'] = line_date
            
            # Determine transaction type - only + symbol indicates credit
            if '+' in line:
                transaction['type'] = 'credit'
            
            # Extract description with improved logic
            description = ''
            # First try the patterns
            for pattern in description_patterns:
                desc_match = re.search(pattern, line, re.IGNORECASE)
                if desc_match:
                    description = desc_match.group(1).strip()
                    # Clean up the description
                    description = re.sub(r'\s+', ' ', description)  # normalize spaces
                    description = re.sub(r'^(?:to|from|by|via|through)\s+', '', description, flags=re.IGNORECASE)
                    if len(description) > 2:  # Allow shorter names but still avoid single characters
                        break
            
            # If no match found, try to extract description from the part before the amount
            if not description:
                pre_amount = line[:amount_match.start()].strip()
                # Remove common prefixes and clean up
                pre_amount = re.sub(r'^(?:to|from|by|via|through)\s+', '', pre_amount, flags=re.IGNORECASE)
                pre_amount = re.sub(r'\s+', ' ', pre_amount)  # normalize spaces
                if len(pre_amount) > 2:
                    description = pre_amount

            # Final cleanup of description
            if description:
                # Remove any trailing transaction identifiers
                description = re.sub(r'\s*(?:UPI|IMPS|NEFT|RTGS|REF|ID|NO)[:\s]*(?:\d+|[A-Z0-9]+)?$', '', description, flags=re.IGNORECASE)
                description = description.strip()
            
            transaction['description'] = description or 'Unknown Transaction'
            
            # Make duplicate detection less strict by normalizing values
            transaction_key = f"{transaction['date']}_{transaction['amount']}_{transaction['type']}"
            
            # Check for duplicates
            if transaction_key in seen_transactions:
                continue
            
            # Add transaction if we have both amount and description
            if transaction['amount'] > 0:
                seen_transactions.add(transaction_key)
                transactions.append(transaction)
        
        return transactions