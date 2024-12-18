# MoneyApp Backup (December 14, 2024)

This is a backup of the MoneyApp codebase with working OCR and bank statement parsing functionality.

## Features Working

1. **OCR Processing**
   - Successfully extracts transactions from screenshots
   - Handles various date formats
   - Extracts transaction amounts and descriptions
   - Detects transaction types (credit/debit)
   - Handles UPI, NEFT, and IMPS transactions

2. **Frontend**
   - Drag and drop interface for uploading files
   - Displays transaction summary
   - Shows transaction list with details
   - Supports both image and PDF uploads

3. **Backend**
   - FastAPI server with proper error handling
   - Separate endpoints for images and bank statements
   - Transaction deduplication
   - Category management
   - Transaction storage in JSON format

## Key Files

- `src/main.py`: FastAPI server and endpoints
- `src/ocr_handler.py`: OCR processing and transaction extraction
- `src/bank_parser.py`: Bank statement parsing for various banks
- `src/static/js/main.js`: Frontend JavaScript code
- `src/static/index.html`: Main HTML interface
- `src/static/css/styles.css`: CSS styles

## Dependencies

- Python packages: FastAPI, pdfplumber, pytesseract, Pillow, pandas
- Frontend: Tailwind CSS
- System: Tesseract OCR

## Known Working Features

1. Screenshot Processing
   - Successfully extracts transactions from bank screenshots
   - Handles various formats and layouts
   - Good accuracy in text extraction
   - Proper handling of amounts and descriptions

2. Transaction Management
   - Proper storage of transactions
   - Deduplication working
   - Category assignment
   - Transaction listing and filtering
