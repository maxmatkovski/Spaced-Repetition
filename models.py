from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(50), nullable=False)  # e.g., 'card_review', 'reset_progress'
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<UserActivity {self.action} at {self.timestamp}>'

class CardReview(db.Model):
    __tablename__ = 'card_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False)
    card_id = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    algorithm = db.Column(db.String(10), nullable=False)  # 'SM2' or 'FSRS'
    rating = db.Column(db.Integer, nullable=False)  # 1-4
    previous_interval = db.Column(db.Float)
    new_interval = db.Column(db.Float)
    review_time = db.Column(db.Float)  # Time taken for review in seconds
    
    def __repr__(self):
        return f'<CardReview {self.algorithm} card:{self.card_id} rating:{self.rating}>'

class AlgorithmPerformance(db.Model):
    __tablename__ = 'algorithm_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    algorithm = db.Column(db.String(10), nullable=False)
    metrics = db.Column(JSON)  # Stores retention rate, average review time, etc.
    
    def __repr__(self):
        return f'<AlgorithmPerformance {self.algorithm} at {self.timestamp}>'

class Analytics(db.Model):
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    total_reviews = db.Column(db.Integer, default=0)
    unique_sessions = db.Column(db.Integer, default=0)
    avg_retention_sm2 = db.Column(db.Float)
    avg_retention_fsrs = db.Column(db.Float)
    daily_stats = db.Column(JSON)  # Detailed daily statistics
    
    def __repr__(self):
        return f'<Analytics {self.date} reviews:{self.total_reviews}>' 