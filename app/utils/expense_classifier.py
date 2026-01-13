"""
Expense Classifier and Duplicate Detector
Automatically categorizes expenses based on description and merchant name
Uses ML when available, falls back to keyword-based classification
Also detects duplicate transactions
"""

import re
from datetime import timedelta
from sqlalchemy import and_, or_
from app.models import Expense, Category
from difflib import SequenceMatcher

try:
    from app.utils.ml_classifier import MLExpenseClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class ExpenseClassifier:
    """Classifies expenses into categories based on description patterns"""
    
    # Category keyword mappings
    CATEGORY_KEYWORDS = {
        'Food & Dining': [
            'restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'food', 'kitchen',
            'swiggy', 'zomato', 'ubereats', 'delivery', 'dining', 'breakfast',
            'lunch', 'dinner', 'snacks', 'bakery', 'juice', 'meal', 'eat',
            'mcdonald', 'kfc', 'subway', 'starbucks', 'dominos', 'biryani',
            'hotel', 'dosa', 'idli', 'thali', 'dhaba', 'amudham'
        ],
        'Transportation': [
            'uber', 'ola', 'taxi', 'metro', 'bus', 'petrol', 'diesel', 'fuel',
            'parking', 'toll', 'rapido', 'train', 'railway', 'flight', 'airline',
            'auto', 'rickshaw', 'ride', 'cab', 'transport', 'vehicle', 'bike'
        ],
        'Shopping': [
            'grocery', 'supermarket', 'market', 'bigbasket', 'blinkit', 'instamart',
            'dunzo', 'vegetables', 'fruits', 'store', 'mart', 'bazaar', 'provisions',
            'fresh', 'reliance', 'more', 'dmart', 'walmart', 'amazon fresh',
            'amazon', 'flipkart', 'myntra', 'ajio', 'shopping', 'mall',
            'fashion', 'clothing', 'shoes', 'accessories', 'electronics', 'gadgets',
            'online', 'purchase', 'buy', 'shop', 'retail', 'outlet', 'brand'
        ],
        'Entertainment': [
            'movie', 'cinema', 'pvr', 'inox', 'theatre', 'game', 'gaming', 'steam',
            'playstation', 'xbox', 'nintendo', 'bookmyshow', 'concert', 'event',
            'netflix', 'prime', 'hotstar', 'spotify', 'youtube', 'subscription',
            'entertainment', 'fun', 'amusement', 'park', 'club', 'playo', 'square'
        ],
        'Healthcare': [
            'hospital', 'clinic', 'doctor', 'medical', 'pharmacy', 'medicine',
            'health', 'apollo', 'practo', '1mg', 'pharmeasy', 'medlife', 'diagnostic',
            'lab', 'test', 'checkup', 'consultation', 'dental', 'physiotherapy',
            'gym', 'fitness', 'yoga', 'wellness'
        ],
        'Housing & Utilities': [
            'electricity', 'water', 'gas', 'internet', 'broadband', 'mobile',
            'phone', 'recharge', 'bill', 'utility', 'maintenance', 'rent',
            'emi', 'loan', 'credit card', 'insurance', 'premium'
        ],
        'Education': [
            'education', 'school', 'college', 'university', 'course', 'tuition',
            'training', 'workshop', 'seminar', 'udemy', 'coursera', 'book', 'books',
            'library', 'study', 'learning', 'class', 'coaching'
        ],
        'Other': [
            'personal', 'salon', 'spa', 'grooming', 'haircut', 'beauty', 'cosmetic',
            'care', 'parlour', 'barber', 'skincare', 'makeup', 'travel',
            'hotel', 'booking', 'airbnb', 'oyo', 'resort', 'vacation', 'trip',
            'tourism', 'goibibo', 'makemytrip', 'yatra', 'cleartrip',
            'holiday', 'tour', 'package', 'miscellaneous', 'misc'
        ]
    }
    
    def __init__(self, user_id, db_session):
        self.user_id = user_id
        self.db = db_session
        self.categories = self._load_categories()
        
        # Initialize ML classifier if available
        self.ml_classifier = None
        self.use_ml = False
        if ML_AVAILABLE:
            try:
                self.ml_classifier = MLExpenseClassifier(user_id, db_session)
                # Check if model is trained
                if self.ml_classifier.last_trained is not None:
                    self.use_ml = True
                    print(f"🤖 Using ML classifier (trained on {self.ml_classifier.training_size} samples)")
                else:
                    # Try to train if enough data
                    if self.ml_classifier.needs_training(min_samples=20):
                        result = self.ml_classifier.train()
                        if result['success']:
                            self.use_ml = True
                            print(f"✨ ML model trained: {result['sample_count']} samples, "
                                  f"{result.get('accuracy', 0)*100:.1f}% accuracy")
            except Exception as e:
                print(f"⚠️ ML classifier initialization failed: {e}")
                self.use_ml = False
    
    def _load_categories(self):
        """Load user's categories"""
        return {
            cat.name: cat.id 
            for cat in Category.query.filter(
                or_(
                    Category.user_id == self.user_id,
                    Category.user_id == None
                ),
                Category.is_active == True
            ).all()
        }
    
    def classify(self, title, description=None, confidence_threshold=0.6):
        """
        Classify expense based on title and optional description
        Uses ML if available and confident enough, otherwise falls back to keywords
        
        Args:
            title: Expense title (required)
            description: Optional expense description for additional context
            confidence_threshold: Minimum confidence for ML prediction (0-1)
        
        Returns:
            tuple: (category_id, method) where method is 'ml' or 'keyword'
        """
        # Combine title and description for better context (matching training format)
        text = title
        if description:
            text += " " + description
        
        # Try ML first if available
        if self.use_ml and self.ml_classifier:
            try:
                category_id, probabilities = self.ml_classifier.predict(
                    text, 
                    return_probabilities=True
                )
                
                if category_id and probabilities:
                    # Get confidence (max probability)
                    confidence = max(probabilities.values())
                    
                    if confidence >= confidence_threshold:
                        print(f"🎯 ML classified with {confidence*100:.1f}% confidence")
                        return category_id, 'ml'
                    else:
                        print(f"⚠️ ML confidence too low ({confidence*100:.1f}%), using keywords")
            except Exception as e:
                print(f"⚠️ ML prediction failed: {e}, falling back to keywords")
        
        # Fall back to keyword-based classification
        category_id = self._classify_by_keywords(text)
        return category_id, 'keyword'
    
    def _classify_by_keywords(self, description):
        """Original keyword-based classification"""
        description_lower = description.lower()
        print(f"🔍 Classifying: '{description}' (lowercase: '{description_lower}')")
        print(f"📚 Available categories: {list(self.categories.keys())}")
        
        # Score each category
        category_scores = {}
        for category_name, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                # Check if keyword is in description
                if keyword in description_lower:
                    # Give higher score for exact word matches
                    if re.search(r'\b' + re.escape(keyword) + r'\b', description_lower):
                        score += 2
                    else:
                        score += 1
            
            if score > 0:
                category_scores[category_name] = score
        
        print(f"📊 Category scores: {category_scores}")
        
        # Return category with highest score
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            category_id = self.categories.get(best_category)
            print(f"✅ Best match: {best_category} (ID: {category_id})")
            return category_id
        
        # Default to 'Other' if available
        print(f"⚠️ No match found, returning 'Other' category")
        return self.categories.get('Other')
    
    def retrain_model(self):
        """
        Retrain the ML model with latest data
        Call this after adding new expenses
        
        Returns:
            dict: Training results
        """
        if not ML_AVAILABLE or not self.ml_classifier:
            return {'success': False, 'message': 'ML not available'}
        
        return self.ml_classifier.train()
    
    def should_retrain(self):
        """Check if model should be retrained"""
        if not self.use_ml or not self.ml_classifier:
            return False
        return self.ml_classifier.needs_training(min_samples=20, min_new_samples=10)
    
    def get_category_name(self, category_id):
        """Get category name from ID"""
        for name, cid in self.categories.items():
            if cid == category_id:
                return name
        return 'Unknown'


class DuplicateDetector:
    """Detects duplicate expense transactions"""
    
    def __init__(self, user_id, db_session):
        self.user_id = user_id
        self.db = db_session
    
    def is_duplicate(self, title, amount, date, threshold=0.85):
        """
        Check if an expense is a duplicate
        
        Args:
            title: Expense title/description
            amount: Expense amount
            date: Expense date
            threshold: Similarity threshold (0-1) for fuzzy matching
        
        Returns:
            tuple: (is_duplicate: bool, existing_expense: Expense or None)
        """
        # Check for exact matches within ±2 days
        date_range_start = date - timedelta(days=2)
        date_range_end = date + timedelta(days=2)
        
        # First check: Exact amount and date match
        exact_match = Expense.query.filter(
            Expense.user_id == self.user_id,
            Expense.amount == amount,
            Expense.date == date
        ).first()
        
        if exact_match:
            # Check title similarity
            similarity = self._text_similarity(title, exact_match.title)
            if similarity > threshold:
                return True, exact_match
        
        # Second check: Same amount within date range with similar title
        potential_duplicates = Expense.query.filter(
            Expense.user_id == self.user_id,
            Expense.amount == amount,
            Expense.date.between(date_range_start, date_range_end)
        ).all()
        
        for expense in potential_duplicates:
            similarity = self._text_similarity(title, expense.title)
            if similarity > threshold:
                return True, expense
        
        # Third check: Very similar title and amount (within 1%) on same date
        amount_lower = amount * 0.99
        amount_upper = amount * 1.01
        
        same_date_expenses = Expense.query.filter(
            Expense.user_id == self.user_id,
            Expense.date == date,
            Expense.amount.between(amount_lower, amount_upper)
        ).all()
        
        for expense in same_date_expenses:
            similarity = self._text_similarity(title, expense.title)
            if similarity > 0.9:  # Higher threshold for amount fuzzy match
                return True, expense
        
        return False, None
    
    def _text_similarity(self, text1, text2):
        """Calculate similarity between two strings (0-1)"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, text1, text2).ratio()
    
    def find_all_duplicates(self, limit=100):
        """
        Find all potential duplicate expenses
        
        Returns:
            list: List of tuples (expense1, expense2, similarity_score)
        """
        duplicates = []
        
        # Get recent expenses
        expenses = Expense.query.filter(
            Expense.user_id == self.user_id
        ).order_by(Expense.date.desc()).limit(limit).all()
        
        # Check each pair
        for i, exp1 in enumerate(expenses):
            for exp2 in expenses[i+1:]:
                # Skip if dates are too far apart
                date_diff = abs((exp1.date - exp2.date).days)
                if date_diff > 7:
                    continue
                
                # Check if amounts match
                if exp1.amount == exp2.amount:
                    similarity = self._text_similarity(exp1.title, exp2.title)
                    if similarity > 0.8:
                        duplicates.append((exp1, exp2, similarity))
        
        return sorted(duplicates, key=lambda x: x[2], reverse=True)
    
    def merge_duplicates(self, keep_id, delete_id):
        """
        Merge duplicate expenses by keeping one and deleting the other
        
        Args:
            keep_id: ID of expense to keep
            delete_id: ID of expense to delete
        
        Returns:
            bool: Success status
        """
        try:
            keep_expense = Expense.query.filter_by(
                id=keep_id, user_id=self.user_id
            ).first()
            
            delete_expense = Expense.query.filter_by(
                id=delete_id, user_id=self.user_id
            ).first()
            
            if not keep_expense or not delete_expense:
                return False
            
            # Delete the duplicate
            self.db.delete(delete_expense)
            self.db.commit()
            
            return True
        except Exception as e:
            self.db.rollback()
            return False
