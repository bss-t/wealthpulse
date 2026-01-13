"""
Machine Learning Expense Classifier
Learns from user's transaction history and continuously improves
Uses scikit-learn for training and prediction
"""

import os
import pickle
import numpy as np
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sqlalchemy import func
from app.models import Expense, Category, Investment, InvestmentType


class MLExpenseClassifier:
    """
    Machine Learning-based expense classifier that learns from user's history
    """
    
    def __init__(self, user_id, db_session, models_dir='ml_models'):
        self.user_id = user_id
        self.db = db_session
        self.models_dir = models_dir
        self.model_path = os.path.join(models_dir, f'expense_classifier_user_{user_id}.pkl')
        self.metadata_path = os.path.join(models_dir, f'expense_metadata_user_{user_id}.pkl')
        
        # Ensure models directory exists
        os.makedirs(models_dir, exist_ok=True)
        
        # Load or create model
        self.model = None
        self.vectorizer = None
        self.categories = {}
        self.category_names = []
        self.last_trained = None
        self.training_size = 0
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path) and os.path.exists(self.metadata_path):
            try:
                # Load existing model
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['pipeline']
                    self.vectorizer = self.model.named_steps['tfidf']
                
                with open(self.metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    self.categories = metadata['categories']
                    self.category_names = metadata['category_names']
                    self.last_trained = metadata.get('last_trained')
                    self.training_size = metadata.get('training_size', 0)
                
                print(f"✅ Loaded ML model for user {self.user_id} (trained on {self.training_size} samples)")
            except Exception as e:
                print(f"⚠️ Error loading model: {e}. Creating new model.")
                self._create_new_model()
        else:
            self._create_new_model()
    
    def _create_new_model(self):
        """Create new ML model"""
        # Create pipeline with TF-IDF and Naive Bayes
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 2),  # Use unigrams and bigrams
                min_df=1,
                strip_accents='unicode',
                lowercase=True,
                token_pattern=r'\b[a-zA-Z]{2,}\b'  # Words with 2+ letters
            )),
            ('classifier', MultinomialNB(alpha=0.1))
        ])
        
        # Load categories
        self._load_categories()
        
        print(f"✨ Created new ML model for user {self.user_id}")
    
    def _load_categories(self):
        """Load user's categories"""
        cats = Category.query.filter(
            Category.user_id.in_([self.user_id, None]),
            Category.is_active == True
        ).all()
        
        self.categories = {cat.name: cat.id for cat in cats}
        self.category_names = list(self.categories.keys())
    
    def needs_training(self, min_samples=20, min_new_samples=10):
        """
        Check if model needs retraining
        
        Args:
            min_samples: Minimum total samples needed for initial training
            min_new_samples: Minimum new samples since last training
        
        Returns:
            bool: True if training needed
        """
        # Get total expense count
        total_count = Expense.query.filter_by(user_id=self.user_id).count()
        
        # Check if we have minimum samples
        if total_count < min_samples:
            return False
        
        # If never trained, train now
        if self.last_trained is None:
            return True
        
        # Check if we have enough new samples
        new_samples = total_count - self.training_size
        if new_samples >= min_new_samples:
            return True
        
        return False
    
    def train(self, min_samples_per_category=3):
        """
        Train the ML model on user's expense history
        
        Args:
            min_samples_per_category: Minimum samples required per category
        
        Returns:
            dict: Training results (accuracy, sample count, etc.)
        """
        # Get all labeled expenses
        expenses = Expense.query.filter_by(user_id=self.user_id).all()
        
        if len(expenses) < 10:
            return {
                'success': False,
                'message': 'Not enough expenses to train (minimum 10 required)',
                'sample_count': len(expenses)
            }
        
        # Prepare training data
        texts = []
        labels = []
        category_counts = {}
        
        for expense in expenses:
            # Combine title and description for better context
            text = expense.title
            if expense.description:
                text += " " + expense.description
            
            texts.append(text)
            labels.append(expense.category.name)
            
            # Track category distribution
            cat_name = expense.category.name
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        # Check if we have enough samples per category
        valid_categories = [cat for cat, count in category_counts.items() 
                           if count >= min_samples_per_category]
        
        if len(valid_categories) < 2:
            return {
                'success': False,
                'message': f'Need at least 2 categories with {min_samples_per_category}+ samples each',
                'category_counts': category_counts
            }
        
        # Filter to only include valid categories
        filtered_texts = []
        filtered_labels = []
        for text, label in zip(texts, labels):
            if label in valid_categories:
                filtered_texts.append(text)
                filtered_labels.append(label)
        
        try:
            # Train the model
            self.model.fit(filtered_texts, filtered_labels)
            
            # Calculate accuracy with cross-validation if enough samples
            accuracy = 0.0
            if len(filtered_texts) >= 20:
                # Split for validation
                X_train, X_test, y_train, y_test = train_test_split(
                    filtered_texts, filtered_labels, test_size=0.2, random_state=42
                )
                self.model.fit(X_train, y_train)
                accuracy = self.model.score(X_test, y_test)
            
            # Save model
            self.last_trained = datetime.now()
            self.training_size = len(filtered_texts)
            
            with open(self.model_path, 'wb') as f:
                pickle.dump({'pipeline': self.model}, f)
            
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({
                    'categories': self.categories,
                    'category_names': valid_categories,
                    'last_trained': self.last_trained,
                    'training_size': self.training_size,
                    'category_counts': category_counts
                }, f)
            
            return {
                'success': True,
                'accuracy': accuracy,
                'sample_count': len(filtered_texts),
                'category_counts': category_counts,
                'valid_categories': valid_categories
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Training error: {str(e)}',
                'sample_count': len(filtered_texts)
            }
    
    def predict(self, text, return_probabilities=False):
        """
        Predict category for expense text
        
        Args:
            text: Expense description
            return_probabilities: If True, return probability for each category
        
        Returns:
            category_id or (category_id, probabilities_dict)
        """
        if self.model is None or self.last_trained is None:
            return None if not return_probabilities else (None, {})
        
        try:
            # Predict
            predicted_category_name = self.model.predict([text])[0]
            category_id = self.categories.get(predicted_category_name)
            
            if return_probabilities:
                # Get probabilities for all categories
                probas = self.model.predict_proba([text])[0]
                proba_dict = {}
                
                # Get class labels from the classifier
                classes = self.model.named_steps['classifier'].classes_
                
                for cat_name, proba in zip(classes, probas):
                    proba_dict[cat_name] = float(proba)
                
                return category_id, proba_dict
            
            return category_id
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return None if not return_probabilities else (None, {})
    
    def get_confidence(self, text):
        """Get prediction confidence (probability of predicted class)"""
        if self.model is None or self.last_trained is None:
            return 0.0
        
        try:
            probas = self.model.predict_proba([text])[0]
            return float(max(probas))
        except:
            return 0.0


class MLInvestmentClassifier:
    """
    Machine Learning-based investment type classifier
    Similar to expense classifier but for investments
    """
    
    def __init__(self, user_id, db_session, models_dir='ml_models'):
        self.user_id = user_id
        self.db = db_session
        self.models_dir = models_dir
        self.model_path = os.path.join(models_dir, f'investment_classifier_user_{user_id}.pkl')
        self.metadata_path = os.path.join(models_dir, f'investment_metadata_user_{user_id}.pkl')
        
        os.makedirs(models_dir, exist_ok=True)
        
        self.model = None
        self.investment_types = {}
        self.last_trained = None
        self.training_size = 0
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path) and os.path.exists(self.metadata_path):
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['pipeline']
                
                with open(self.metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    self.investment_types = metadata['investment_types']
                    self.last_trained = metadata.get('last_trained')
                    self.training_size = metadata.get('training_size', 0)
                
                print(f"✅ Loaded investment ML model for user {self.user_id}")
            except Exception as e:
                print(f"⚠️ Error loading investment model: {e}")
                self._create_new_model()
        else:
            self._create_new_model()
    
    def _create_new_model(self):
        """Create new ML model for investments"""
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=300,
                ngram_range=(1, 2),
                min_df=1,
                lowercase=True
            )),
            ('classifier', MultinomialNB(alpha=0.1))
        ])
        
        # Load investment types
        inv_types = InvestmentType.query.filter(
            InvestmentType.user_id.in_([self.user_id, None]),
            InvestmentType.is_active == True
        ).all()
        
        self.investment_types = {it.name: it.id for it in inv_types}
    
    def train(self):
        """Train model on user's investment history"""
        investments = Investment.query.filter_by(user_id=self.user_id).all()
        
        if len(investments) < 5:
            return {
                'success': False,
                'message': 'Not enough investments to train (minimum 5 required)',
                'sample_count': len(investments)
            }
        
        texts = []
        labels = []
        
        for inv in investments:
            text = inv.name
            if inv.notes:
                text += " " + inv.notes
            texts.append(text)
            labels.append(inv.type.name)
        
        try:
            self.model.fit(texts, labels)
            self.last_trained = datetime.now()
            self.training_size = len(texts)
            
            with open(self.model_path, 'wb') as f:
                pickle.dump({'pipeline': self.model}, f)
            
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({
                    'investment_types': self.investment_types,
                    'last_trained': self.last_trained,
                    'training_size': self.training_size
                }, f)
            
            return {
                'success': True,
                'sample_count': len(texts)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Training error: {str(e)}'
            }
    
    def predict(self, text):
        """Predict investment type"""
        if self.model is None or self.last_trained is None:
            return None
        
        try:
            predicted_type_name = self.model.predict([text])[0]
            return self.investment_types.get(predicted_type_name)
        except:
            return None
