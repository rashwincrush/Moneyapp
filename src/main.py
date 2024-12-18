from fastapi import FastAPI, UploadFile, HTTPException, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from typing import Dict, Any, List
import io
from datetime import datetime
import json
import os
from pydantic import BaseModel

from .ocr_handler import OCRHandler
from .categorizer import TransactionCategorizer
from .bank_parser import BankStatementParser

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Define transactions file path
TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')

# Create empty transactions file if it doesn't exist
if not os.path.exists(TRANSACTIONS_FILE):
    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump([], f)

# Define transaction categories
TRANSACTION_CATEGORIES = [
    'Food & Dining',
    'Shopping',
    'Transportation',
    'Bills & Utilities',
    'Entertainment',
    'Health & Medical',
    'Travel',
    'Education',
    'Business',
    'Investments',
    'Salary',
    'Other'
]

app = FastAPI(
    title="MoneyApp API",
    description="""
    MoneyApp API processes transaction screenshots and extracts relevant information.
    
    Features:
    * OCR processing of transaction images
    * Automatic detection of transaction type (credit/debit)
    * Amount extraction with currency symbol handling
    * Party name extraction
    * Transaction categorization
    """,
    version="1.0.0",
    contact={
        "name": "MoneyApp Support",
    }
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/templates")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add supported banks to the app state
SUPPORTED_BANKS = BankStatementParser.SUPPORTED_BANKS

class CategoryUpdate(BaseModel):
    category: str

class TransactionCategoryUpdate(BaseModel):
    transaction_id: int
    category: str

def load_transactions() -> List[Dict]:
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            transactions = json.load(f)
            # Sort transactions by date and timestamp
            return sorted(transactions, 
                        key=lambda x: (x.get('date', ''), x.get('timestamp', '')), 
                        reverse=True)
    except:
        return []

def save_transaction(transaction: Dict):
    """Save a transaction to the JSON file, checking for duplicates."""
    transactions = load_transactions()
    
    # Add default category if not present
    if 'category' not in transaction:
        transaction['category'] = 'Other'
    
    # Add timestamp if not present
    if 'timestamp' not in transaction:
        transaction['timestamp'] = datetime.now().isoformat()
    
    # Create a unique key for the new transaction
    new_key = f"{transaction['date']}_{transaction['amount']}_{transaction['description']}_{transaction['type']}"
    
    # Check if this transaction already exists
    existing_keys = {f"{t['date']}_{t['amount']}_{t['description']}_{t['type']}" for t in transactions}
    
    if new_key not in existing_keys:
        transactions.append(transaction)
        # Sort transactions before saving
        transactions = sorted(transactions, 
                           key=lambda x: (x.get('date', ''), x.get('timestamp', '')), 
                           reverse=True)
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump(transactions, f, indent=2)
        return True
    return False

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health", 
    summary="Health Check",
    description="Returns the health status of the API",
    response_description="Returns healthy if the API is running"
)
async def health_check():
    """
    Performs a health check of the API.
    
    Returns:
        dict: A dictionary containing the health status
    """
    return {"status": "healthy"}

@app.get("/transactions/summary")
async def get_transactions_summary():
    """
    Get a summary of all transactions.
    
    Returns:
        Dict containing:
        - total_credit: Total amount credited
        - total_debit: Total amount debited
        - transactions: List of all transactions
    """
    try:
        transactions = load_transactions()
        
        total_credit = 0
        total_debit = 0
        
        for transaction in transactions:
            amount = float(transaction.get('amount', 0))
            if transaction.get('type') == 'credit':
                total_credit += amount
            else:
                total_debit += amount
        
        return {
            "total_credit": round(total_credit, 2),
            "total_debit": round(total_debit, 2),
            "transactions": sorted(transactions, 
                                key=lambda x: x.get('timestamp', ''), 
                                reverse=True)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/categories")
async def get_categories():
    """Get all available transaction categories."""
    return {"categories": TRANSACTION_CATEGORIES}

@app.get("/banks")
async def get_banks():
    """Get list of supported banks."""
    return {"banks": SUPPORTED_BANKS}

@app.post("/transactions/process")
async def process_transaction(image: UploadFile) -> Dict[str, Any]:
    """
    Process a transaction image and extract all transactions.
    
    Args:
        image (UploadFile): The image file containing transaction details
        
    Returns:
        Dict[str, Any]: Dictionary containing extracted transaction details
    """
    try:
        # Validate file type
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
            
        # Read image content
        image_bytes = await image.read()
        
        # Process image with OCR
        text = OCRHandler.process_image(image_bytes)
        
        # Extract all transactions
        transactions = OCRHandler.extract_transactions(text)
        
        if not transactions:
            raise HTTPException(status_code=400, detail="No valid transactions found in the image")
        
        # Add timestamp to each transaction
        timestamp = datetime.now().isoformat()
        for transaction in transactions:
            transaction['timestamp'] = timestamp
        
        # Save non-duplicate transactions
        saved_count = 0
        skipped_count = 0
        for transaction in transactions:
            if save_transaction(transaction):
                saved_count += 1
            else:
                skipped_count += 1
        
        message = f"Successfully processed {saved_count} new transaction(s)"
        if skipped_count > 0:
            message += f", skipped {skipped_count} duplicate(s)"
        
        return {
            "message": message,
            "transactions": transactions,
            "saved_count": saved_count,
            "skipped_count": skipped_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transactions/process-statement", 
    summary="Process bank statement",
    description="""
    Upload and process a bank statement file (PDF or CSV).
    The bank type will be automatically detected from the statement format.
    
    Supported banks:
    - HDFC Bank
    - State Bank of India (SBI)
    - ICICI Bank
    - Axis Bank
    - Kotak Mahindra Bank
    
    Supported file formats:
    - PDF bank statements
    - CSV bank statements
    
    File size limit: 10MB
    """,
    response_model=dict,
    responses={
        200: {
            "description": "Successfully processed bank statement",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully processed 10 transactions from HDFC Bank",
                        "bank": "HDFC Bank",
                        "transactions_count": 10,
                        "transactions": [
                            {
                                "date": "2024-01-01",
                                "description": "Sample Transaction",
                                "amount": 1000.00,
                                "type": "credit",
                                "category": "Other",
                                "bank": "HDFC Bank"
                            }
                        ]
                    }
                }
            }
        },
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Unsupported file format. Please upload a PDF or CSV file"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error processing file: [error details]"
                    }
                }
            }
        }
    }
)
async def process_bank_statement(
    file: UploadFile = File(..., description="Bank statement file (PDF or CSV)")
):
    """
    Process a bank statement file (PDF or CSV) and extract transactions.
    Bank type will be automatically detected from the statement format.
    """
    try:
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
            
        if len(content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Get file extension
        if not file.filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
            
        file_extension = file.filename.lower().split('.')[-1]
        if file_extension not in ['pdf', 'csv']:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format: {file_extension}. Please upload a PDF or CSV file"
            )
        
        # Create parser instance and auto-detect bank
        parser = BankStatementParser()
        
        try:
            # Parse statement and detect bank
            transactions = parser.parse_statement(content, file_extension)
            detected_bank = parser.bank_type
            
            if not detected_bank:
                raise ValueError("Could not detect bank from statement")
                
            if not transactions:
                raise ValueError("No transactions found in statement")
            
            # Save transactions with bank information
            saved_count = 0
            for transaction in transactions:
                # Add bank information to transaction
                transaction['bank'] = BankStatementParser.SUPPORTED_BANKS[detected_bank]
                if save_transaction(transaction):
                    saved_count += 1
            
            return {
                "message": f"Successfully processed {saved_count} transactions from {BankStatementParser.SUPPORTED_BANKS[detected_bank]}",
                "bank": BankStatementParser.SUPPORTED_BANKS[detected_bank],
                "transactions_count": saved_count,
                "transactions": transactions[:5]  # Return first 5 transactions as preview
            }
            
        except ValueError as e:
            # Client-side errors (invalid format, unsupported bank, etc.)
            raise HTTPException(status_code=400, detail=str(e))
            
    except HTTPException:
        # Re-raise HTTP exceptions as is
        raise
        
    except Exception as e:
        # Log unexpected errors
        print(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
        
    finally:
        await file.close()

@app.post("/transactions/clear")
async def clear_transactions():
    """Clear all stored transactions."""
    try:
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump([], f)
        return {"message": "All transactions cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/transactions/{transaction_id}/category")
async def update_transaction_category(transaction_id: int, update: CategoryUpdate):
    """Update the category of a specific transaction."""
    try:
        if update.category not in TRANSACTION_CATEGORIES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid category. Must be one of: {', '.join(TRANSACTION_CATEGORIES)}"
            )
        
        transactions = load_transactions()
        if 0 <= transaction_id < len(transactions):
            # Store old category for logging
            old_category = transactions[transaction_id].get('category', 'Other')
            
            # Update category
            transactions[transaction_id]['category'] = update.category
            
            # Update timestamp
            transactions[transaction_id]['timestamp'] = datetime.now().isoformat()
            
            # Sort and save transactions
            transactions = sorted(
                transactions, 
                key=lambda x: (x.get('date', ''), x.get('timestamp', '')), 
                reverse=True
            )
            
            with open(TRANSACTIONS_FILE, 'w') as f:
                json.dump(transactions, f, indent=2)
            
            print(f"Category updated for transaction {transaction_id}: {old_category} -> {update.category}")
            
            return {
                "message": "Category updated successfully",
                "transaction_id": transaction_id,
                "old_category": old_category,
                "new_category": update.category
            }
        
        raise HTTPException(
            status_code=404, 
            detail=f"Transaction with ID {transaction_id} not found"
        )
        
    except Exception as e:
        print(f"Error updating category for transaction {transaction_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error updating category: {str(e)}"
        )

@app.post('/transactions/update-categories')
async def update_categories(updated_categories: dict):
    try:
        transactions = load_transactions()
        for transaction_id, category in updated_categories.items():
            if int(transaction_id) < len(transactions):
                if category not in TRANSACTION_CATEGORIES:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid category. Must be one of: {', '.join(TRANSACTION_CATEGORIES)}"
                    )
                transactions[int(transaction_id)]['category'] = category
                transactions[int(transaction_id)]['timestamp'] = datetime.now().isoformat()
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Transaction with ID {transaction_id} not found"
                )
        transactions = sorted(
            transactions, 
            key=lambda x: (x.get('date', ''), x.get('timestamp', '')), 
            reverse=True
        )
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump(transactions, f, indent=2)
        return {'message': 'Categories updated successfully'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, reload=True)