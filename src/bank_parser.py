import pdfplumber
import re
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import io

class BankStatementParser:
    SUPPORTED_BANKS = {
        'hdfc': 'HDFC Bank',
        'sbi': 'State Bank of India',
        'icici': 'ICICI Bank',
        'axis': 'Axis Bank',
        'kotak': 'Kotak Mahindra Bank'
    }

    BANK_IDENTIFIERS = {
        'hdfc': ['HDFC BANK', 'HDFC Bank Statement', 'HDFCBank'],
        'sbi': ['State Bank of India', 'SBI Statement', 'www.onlinesbi.com'],
        'icici': ['ICICI Bank', 'ICICI Bank Statement', 'www.icicibank.com'],
        'axis': ['Axis Bank', 'Axis Bank Statement', 'www.axisbank.com'],
        'kotak': ['Kotak Mahindra Bank', 'Kotak Statement', 'www.kotak.com']
    }

    def __init__(self):
        """Initialize parser without requiring bank type."""
        self.bank_type = None

    def detect_bank_from_pdf(self, pdf_content: bytes) -> str:
        """Detect bank type from PDF content."""
        try:
            print("\n=== Starting bank detection from PDF ===")
            pdf_file = io.BytesIO(pdf_content)
            with pdfplumber.open(pdf_file) as pdf:
                print(f"PDF opened successfully, {len(pdf.pages)} pages found")
                # Check first two pages for bank identifiers
                for page_num in range(min(2, len(pdf.pages))):
                    print(f"\nChecking page {page_num + 1} for bank identifiers")
                    text = pdf.pages[page_num].extract_text()
                    if text:
                        print(f"Text extracted from page {page_num + 1}:")
                        print("=== Start of text ===")
                        print(text[:500])  # Print first 500 chars
                        print("=== End of text ===")
                        bank_type = self._identify_bank(text)
                        if bank_type:
                            print(f"Bank identified as: {bank_type}")
                            return bank_type
                        else:
                            print("No bank identifiers found in text")
                    else:
                        print(f"No text could be extracted from page {page_num + 1}")
                
                print("\nTrying to extract text from all pages...")
                # If no bank found in first two pages, try all pages
                for page_num in range(len(pdf.pages)):
                    text = pdf.pages[page_num].extract_text()
                    if text:
                        bank_type = self._identify_bank(text)
                        if bank_type:
                            print(f"Bank identified as: {bank_type} on page {page_num + 1}")
                            return bank_type
                
                print("\nNo bank identifiers found in any page, trying OCR...")
                # If still no bank found, try OCR on first page
                first_page = pdf.pages[0]
                image = first_page.to_image()
                ocr_text = image.get_text()
                if ocr_text:
                    print("OCR text extracted:")
                    print("=== Start of OCR text ===")
                    print(ocr_text[:500])
                    print("=== End of OCR text ===")
                    bank_type = self._identify_bank(ocr_text)
                    if bank_type:
                        print(f"Bank identified from OCR: {bank_type}")
                        return bank_type
                
        except Exception as e:
            print(f"Error in bank detection: {str(e)}")
            raise Exception(f"Error detecting bank from PDF: {str(e)}")
        
        print("Failed to detect bank from PDF")
        raise ValueError("Unable to detect bank type from statement")

    def _identify_bank(self, text: str) -> Optional[str]:
        """Identify bank from text content."""
        print("\n=== Identifying bank from text ===")
        text = text.upper()
        print("Looking for these identifiers:")
        for bank, identifiers in self.BANK_IDENTIFIERS.items():
            print(f"{bank}: {identifiers}")
            if any(identifier.upper() in text for identifier in identifiers):
                print(f"Found match for {bank}")
                return bank
        print("No bank identifiers found")
        return None

    def parse_statement(self, content: bytes, file_type: str) -> List[Dict]:
        """Parse statement content and return list of transactions."""
        if not content:
            raise ValueError("Empty file content")

        # Detect bank type based on file type
        if file_type == 'pdf':
            self.bank_type = self.detect_bank_from_pdf(content)
            transactions = self.parse_pdf(content)
        elif file_type == 'csv':
            self.bank_type = self.detect_bank_from_csv(content)
            transactions = self.parse_csv(content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        if not transactions:
            raise ValueError(f"No transactions found in {file_type.upper()} statement from {self.SUPPORTED_BANKS.get(self.bank_type, 'Unknown Bank')}")
        
        return transactions

    def parse_pdf(self, pdf_content: bytes) -> List[Dict]:
        """Parse PDF content and return list of transactions."""
        transactions = []
        
        try:
            print("\n=== Starting PDF parsing ===")
            pdf_file = io.BytesIO(pdf_content)
            with pdfplumber.open(pdf_file) as pdf:
                if not pdf.pages:
                    raise ValueError("PDF file has no pages")
                
                print(f"\nProcessing PDF with {len(pdf.pages)} pages")
                for page_num, page in enumerate(pdf.pages):
                    print(f"\nExtracting text from page {page_num + 1}")
                    text = page.extract_text()
                    
                    if not text:
                        print(f"Warning: Page {page_num + 1} has no extractable text")
                        continue
                    
                    # Print first few lines of text for debugging
                    print(f"\nText content from page {page_num + 1}:")
                    print("=== Start of text ===")
                    print(text[:1000])  # Print first 1000 chars
                    print("=== End of text ===")
                    
                    # Try to extract tables if available
                    tables = page.extract_tables()
                    if tables:
                        print(f"\nFound {len(tables)} tables on page {page_num + 1}")
                        for table_num, table in enumerate(tables):
                            if table and len(table) > 0:
                                print(f"\nTable {table_num + 1} content:")
                                for row in table[:5]:  # Print first 5 rows
                                    print(row)
                    
                    page_transactions = self._parse_page(text)
                    if page_transactions:
                        print(f"Found {len(page_transactions)} transactions on page {page_num + 1}")
                        transactions.extend(page_transactions)
                    else:
                        print(f"No transactions found on page {page_num + 1}")
                        
                    # Try parsing tables directly
                    if tables:
                        print("\nTrying to parse tables directly...")
                        for table in tables:
                            if not table:
                                continue
                            table_text = '\n'.join([' '.join([str(cell) if cell else '' for cell in row]) for row in table])
                            table_transactions = self._parse_page(table_text)
                            if table_transactions:
                                print(f"Found {len(table_transactions)} transactions in table")
                                transactions.extend(table_transactions)
                        
        except Exception as e:
            print(f"Error parsing PDF: {str(e)}")
            raise Exception(f"Error parsing PDF: {str(e)}")

        if not transactions:
            print("\nNo transactions found in entire PDF")
            print("Final attempt: Trying to parse using raw text patterns...")
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    raw_text = ""
                    for page in pdf.pages:
                        raw_text += page.extract_text() + "\n"
                    
                    # Look for common transaction patterns
                    print("\nSearching for transaction patterns in raw text...")
                    patterns = [
                        # Date, Description, Amount pattern
                        r'(\d{2}[-/]\d{2}[-/]\d{2,4})\s+([^0-9]+?)\s+([\d,]+\.\d{2})',
                        # Date, Credit/Debit indicator, Amount pattern
                        r'(\d{2}[-/]\d{2}[-/]\d{2,4})[^\n]*?((?:CR|DR|Cr\.|Dr\.|Credit|Debit))[^\n]*?([\d,]+\.\d{2})',
                        r'(\d{2}[-/]\d{2}[-/]\d{2,4})[^\n]*?((?:CR|DR|Cr\.|Dr\.|Credit|Debit))[^\n]*?([\d,]+\.\d{2})',
                    ]
                    
                    for pattern in patterns:
                        matches = re.finditer(pattern, raw_text, re.MULTILINE | re.IGNORECASE)
                        for match in matches:
                            print(f"Found potential transaction: {match.group()}")
                            
            except Exception as e:
                print(f"Error in raw text parsing: {str(e)}")

        return transactions

    def parse_csv(self, csv_content: bytes) -> List[Dict]:
        """Parse CSV content and return list of transactions."""
        try:
            # Read CSV content using pandas
            df = pd.read_csv(pd.io.common.BytesIO(csv_content))
            
            if df.empty:
                raise ValueError("CSV file is empty")
            
            # Convert column names to lowercase for case-insensitive matching
            df.columns = [col.lower().strip() for col in df.columns]
            print(f"Found columns: {', '.join(df.columns)}")
            
            transactions = []
            
            if self.bank_type == 'hdfc':
                required_columns = ['date', 'narration', 'debit', 'credit', 'balance']
                date_format = '%d/%m/%y'
            elif self.bank_type == 'sbi':
                required_columns = ['date', 'description', 'debit', 'credit', 'balance']
                date_format = '%d %b %Y'
            elif self.bank_type == 'icici':
                required_columns = ['date', 'particulars', 'debit', 'credit', 'balance']
                date_format = '%d-%m-%Y'
            elif self.bank_type == 'axis':
                required_columns = ['date', 'particulars', 'debit', 'credit', 'balance']
                date_format = '%d-%m-%Y'
            elif self.bank_type == 'kotak':
                required_columns = ['date', 'narration', 'debit amount', 'credit amount']
                date_format = '%d/%m/%Y'
            else:
                raise ValueError(f"Unsupported bank type: {self.bank_type}")
            
            # Check if required columns exist (case-insensitive)
            missing_columns = []
            for col in required_columns:
                if not any(existing_col.lower() == col.lower() for existing_col in df.columns):
                    missing_columns.append(col)
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    transaction = {}
                    
                    # Parse date
                    date_col = self._find_column(df, required_columns[0])
                    date_str = str(row[date_col]).strip()
                    
                    if not date_str:
                        print(f"Warning: Empty date in row {idx + 1}")
                        continue
                        
                    try:
                        transaction_date = datetime.strptime(date_str, date_format)
                        transaction['date'] = transaction_date.strftime('%Y-%m-%d')
                    except ValueError as e:
                        print(f"Warning: Invalid date format in row {idx + 1}: {date_str}")
                        continue
                    
                    # Get description/narration
                    desc_col = self._find_column(df, required_columns[1])
                    transaction['description'] = str(row[desc_col]).strip()
                    
                    if not transaction['description']:
                        print(f"Warning: Empty description in row {idx + 1}")
                        continue
                    
                    # Get amount and type (credit/debit)
                    debit_col = self._find_column(df, 'debit')
                    credit_col = self._find_column(df, 'credit')
                    
                    debit_amount = row[debit_col]
                    credit_amount = row[credit_col]
                    
                    if pd.notna(credit_amount) and float(str(credit_amount).replace(',', '')) > 0:
                        transaction['amount'] = abs(float(str(credit_amount).replace(',', '')))
                        transaction['type'] = 'credit'
                    elif pd.notna(debit_amount) and float(str(debit_amount).replace(',', '')) > 0:
                        transaction['amount'] = abs(float(str(debit_amount).replace(',', '')))
                        transaction['type'] = 'debit'
                    else:
                        print(f"Warning: No valid amount in row {idx + 1}")
                        continue
                    
                    # Add category and bank
                    transaction['category'] = 'Other'  # Default category
                    transaction['bank'] = self.SUPPORTED_BANKS.get(self.bank_type, 'Unknown Bank')
                    
                    transactions.append(transaction)
                    
                except Exception as e:
                    print(f"Warning: Error processing row {idx + 1}: {str(e)}")
                    continue
            
            return transactions
            
        except Exception as e:
            raise Exception(f"Error parsing CSV: {str(e)}")

    def _find_column(self, df: pd.DataFrame, column_name: str) -> str:
        """Find column name case-insensitively."""
        for col in df.columns:
            if col.lower() == column_name.lower():
                return col
        raise ValueError(f"Column '{column_name}' not found")

    def _parse_page(self, text: str) -> List[Dict]:
        """Parse a single page based on bank type."""
        if not text:
            return []
            
        if self.bank_type == 'hdfc':
            return self._parse_hdfc(text)
        elif self.bank_type == 'axis':
            return self._parse_axis(text)
        elif self.bank_type == 'sbi':
            return self._parse_sbi(text)
        elif self.bank_type == 'icici':
            return self._parse_icici(text)
        elif self.bank_type == 'kotak':
            return self._parse_kotak(text)
        else:
            # Try generic patterns if bank type is unknown
            transactions = []
            patterns = [
                # Date, Description, Amount pattern
                r'(\d{2}[-/]\d{2}[-/]\d{2,4})\s+([^0-9]+?)\s+([\d,]+\.\d{2})',
                # Date, Credit/Debit indicator, Amount pattern
                r'(\d{2}[-/]\d{2}[-/]\d{2,4})[^\n]*?((?:CR|DR|Cr\.|Dr\.|Credit|Debit))[^\n]*?([\d,]+\.\d{2})',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    try:
                        date_str = match.group(1)
                        description = match.group(2).strip() if len(match.groups()) > 2 else "Unknown Transaction"
                        amount_str = match.group(-1)  # Last group is always amount
                        
                        # Determine transaction type
                        type_indicators = ['CR', 'Cr.', 'Credit']
                        transaction_type = 'credit' if any(indicator.lower() in description.lower() for indicator in type_indicators) else 'debit'
                        
                        transaction = {
                            'date': self._parse_date(date_str),
                            'description': description,
                            'amount': self._parse_amount(amount_str),
                            'type': transaction_type,
                            'category': 'Other'  # Default category
                        }
                        transactions.append(transaction)
                        
                    except Exception as e:
                        print(f"Error parsing transaction: {str(e)}")
                        continue
                        
            return transactions

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to standard format."""
        try:
            # Try different date formats
            date_formats = [
                '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
                '%Y-%m-%d', '%Y/%m/%d',
                '%d/%m/%y', '%d-%m-%y', '%d.%m.%y'
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
                except:
                    continue
            
            return None
        except:
            return None

    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float."""
        try:
            # Remove currency symbols and commas
            amount_str = re.sub(r'[₹,]', '', amount_str.strip())
            return float(amount_str)
        except:
            return 0.0

    def _parse_hdfc(self, text: str) -> List[Dict]:
        """Parse HDFC Bank statement format."""
        transactions = []
        try:
            # Common patterns for HDFC statements
            patterns = [
                # Pattern 1: Date, Description with UPI/NEFT/IMPS, Amount
                r'(\d{2}/\d{2}/\d{2})\s+([^0-9]+?(?:UPI|NEFT|IMPS)[^0-9]*?)\s+([\d,]+\.\d{2})\s*(?:Cr|Dr)?',
                # Pattern 2: Date, General Description, Amount
                r'(\d{2}/\d{2}/\d{2})\s+([^0-9]+?)\s+([\d,]+\.\d{2})\s*(?:Cr|Dr)?',
                # Pattern 3: Date, Amount, Description (reversed format)
                r'(\d{2}/\d{2}/\d{2})\s+([\d,]+\.\d{2})\s*(?:Cr|Dr)?\s+([^0-9]+(?:UPI|NEFT|IMPS)?[^0-9]*)',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    try:
                        # Extract components based on pattern
                        if pattern == patterns[2]:  # Reversed format
                            date_str = match.group(1)
                            description = match.group(3).strip()
                            amount_str = match.group(2)
                        else:
                            date_str = match.group(1)
                            description = match.group(2).strip()
                            amount_str = match.group(3)
                        
                        # Determine transaction type
                        type_indicators = ['CR', 'Cr.', 'Credit']
                        transaction_type = 'credit' if any(indicator.lower() in text[match.start():match.end()].lower() 
                                                        for indicator in type_indicators) else 'debit'
                        
                        # Create transaction
                        transaction = {
                            'date': self._parse_date(date_str),
                            'description': description or "Unknown Transaction",
                            'amount': self._parse_amount(amount_str),
                            'type': transaction_type,
                            'category': 'Other'  # Default category
                        }
                        
                        transactions.append(transaction)
                        
                    except Exception as e:
                        print(f"Error parsing HDFC transaction: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error in HDFC parser: {str(e)}")
            
        return transactions

    def _parse_axis(self, text: str) -> List[Dict]:
        """Parse Axis Bank statement format."""
        transactions = []
        try:
            # Multiple Axis Bank format patterns
            patterns = [
                # Pattern 1: Date, Description, Amount (Debit/Credit)
                r'(\d{2}-\d{2}-\d{4})\s+([^0-9]+?)\s+([\d,]+\.\d{2})\s*(?:Cr|Dr)',
                # Pattern 2: Date, Description with UPI/NEFT, Amount
                r'(\d{2}-\d{2}-\d{4})\s+([^0-9]+?(?:UPI|NEFT|IMPS)[^0-9]*?)\s+([\d,]+\.\d{2})',
                # Pattern 3: Transaction number format
                r'(\d{2}\s+[A-Za-z]+\s+\d{4})\s+([^0-9]+?)\s+(-?[\d,]+\.\d{2})',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    try:
                        date_str = match.group(1)
                        description = match.group(2).strip()
                        amount_str = match.group(3)
                        
                        # Clean up description
                        description = re.sub(r'\s+', ' ', description).strip()
                        if not description:
                            continue
                            
                        # Determine transaction type
                        type_indicators = ['CR', 'Cr.', 'Credit']
                        transaction_type = 'credit' if any(indicator.lower() in text[match.start():match.end()].lower() 
                                                        for indicator in type_indicators) else 'debit'
                        
                        transaction = {
                            'date': self._parse_date(date_str),
                            'description': description or "Unknown Transaction",
                            'amount': abs(self._parse_amount(amount_str)),
                            'type': transaction_type,
                            'category': 'Other'  # Default category
                        }
                        
                        transactions.append(transaction)
                        
                    except Exception as e:
                        print(f"Error parsing Axis transaction: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error in Axis parser: {str(e)}")
            
        return transactions

    def _parse_sbi(self, text: str) -> List[Dict]:
        """Parse SBI statement format."""
        transactions = []
        
        # SBI format pattern
        pattern = r'(\d{2}/\d{2}/\d{4})\s+([\w\s\-\/]+?)\s+([\d,]+\.\d{2})\s*(CR|DR)'
        
        for match in re.finditer(pattern, text):
            date_str, description, amount_str, type_str = match.groups()
            
            transaction = {
                'date': self._parse_date(date_str),
                'party_name': description.strip(),
                'amount': self._parse_amount(amount_str),
                'type': 'credit' if type_str == 'CR' else 'debit',
                'category': 'Other',  # Default category
                'bank': 'SBI'
            }
            
            if transaction['date']:
                transactions.append(transaction)
        
        return transactions

    def _parse_icici(self, text: str) -> List[Dict]:
        """Parse ICICI Bank statement format."""
        transactions = []
        
        # ICICI format pattern
        pattern = r'(\d{2}/\d{2}/\d{4})\s+([\w\s\-\/]+?)\s+([\d,]+\.\d{2})\s*(CR|DR)'
        
        for match in re.finditer(pattern, text):
            date_str, description, amount_str, type_str = match.groups()
            
            transaction = {
                'date': self._parse_date(date_str),
                'party_name': description.strip(),
                'amount': self._parse_amount(amount_str),
                'type': 'credit' if type_str == 'CR' else 'debit',
                'category': 'Other',  # Default category
                'bank': 'ICICI'
            }
            
            if transaction['date']:
                transactions.append(transaction)
        
        return transactions

    def _parse_kotak(self, text: str) -> List[Dict]:
        """Parse Kotak Bank statement format."""
        transactions = []
        
        # Kotak format pattern
        pattern = r'(\d{2}/\d{2}/\d{4})\s+([\w\s\-\/]+?)\s+([\d,]+\.\d{2})\s*(CR|DR)'
        
        for match in re.finditer(pattern, text):
            date_str, description, amount_str, type_str = match.groups()
            
            transaction = {
                'date': self._parse_date(date_str),
                'party_name': description.strip(),
                'amount': self._parse_amount(amount_str),
                'type': 'credit' if type_str == 'CR' else 'debit',
                'category': 'Other',  # Default category
                'bank': 'Kotak'
            }
            
            if transaction['date']:
                transactions.append(transaction)
        
        return transactions

    def detect_bank_from_csv(self, csv_content: bytes) -> str:
        """Detect bank type from CSV content."""
        try:
            df = pd.read_csv(pd.io.common.BytesIO(csv_content))
            columns = [col.lower().strip() for col in df.columns]
            
            # Check column patterns for each bank
            if all(col in columns for col in ['date', 'narration', 'debit', 'credit', 'balance']):
                # Try to detect from first few rows
                sample_text = ' '.join(str(val) for val in df.iloc[0].values)
                bank_type = self._identify_bank(sample_text)
                if bank_type:
                    return bank_type
                return 'hdfc'  # Default to HDFC if pattern matches but no specific identifier
            elif all(col in columns for col in ['date', 'description', 'debit', 'credit', 'balance']):
                return 'sbi'
            elif all(col in columns for col in ['date', 'particulars', 'debit', 'credit', 'balance']):
                # Check specific patterns for ICICI vs Axis
                if any('ICICI' in str(val) for val in df.iloc[0].values):
                    return 'icici'
                return 'axis'
            elif all(col in columns for col in ['date', 'narration', 'debit amount', 'credit amount']):
                return 'kotak'
            
        except Exception as e:
            raise Exception(f"Error detecting bank from CSV: {str(e)}")
        
        raise ValueError("Unable to detect bank type from CSV format")
