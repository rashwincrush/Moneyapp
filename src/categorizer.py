class TransactionCategorizer:
    # Define category keywords
    CATEGORIES = {
        'food': ['food', 'restaurant', 'cafe', 'swiggy', 'zomato', 'dinner', 'lunch', 'breakfast'],
        'transport': ['uber', 'ola', 'taxi', 'auto', 'petrol', 'fuel', 'metro', 'bus', 'train'],
        'shopping': ['amazon', 'flipkart', 'mall', 'shop', 'store', 'market'],
        'utilities': ['electricity', 'water', 'gas', 'internet', 'wifi', 'broadband', 'mobile', 'phone'],
        'entertainment': ['movie', 'netflix', 'amazon prime', 'hotstar', 'theatre', 'concert'],
        'health': ['medical', 'medicine', 'hospital', 'doctor', 'pharmacy', 'clinic'],
        'rent': ['rent', 'house rent', 'accommodation'],
        'salary': ['salary', 'payroll', 'income'],
        'investment': ['mutual fund', 'stocks', 'shares', 'investment'],
        'other': []  # Default category
    }
    
    @staticmethod
    def categorize_transaction(transaction_details):
        if not transaction_details.get('notes'):
            return 'other'
            
        notes = transaction_details['notes'].lower()
        transaction_type = transaction_details.get('type', '')
        
        # If it's a credit transaction and contains salary-related keywords
        if transaction_type == 'credit' and any(keyword in notes for keyword in TransactionCategorizer.CATEGORIES['salary']):
            return 'salary'
            
        # Check other categories
        for category, keywords in TransactionCategorizer.CATEGORIES.items():
            if any(keyword in notes for keyword in keywords):
                return category
                
        return 'other'
        
    @staticmethod
    def get_transaction_summary(transaction_details):
        category = TransactionCategorizer.categorize_transaction(transaction_details)
        
        summary = {
            'date': transaction_details.get('date'),
            'amount': transaction_details.get('amount'),
            'type': transaction_details.get('type'),
            'category': category,
            'notes': transaction_details.get('notes')
        }
        
        return summary