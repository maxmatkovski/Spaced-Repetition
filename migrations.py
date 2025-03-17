from flask import Flask
from models import db, UserActivity, CardReview, AlgorithmPerformance, Analytics
from app import app

def upgrade_database():
    """Create new tables for tracking and analytics"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        print("Created the following tables:")
        print("- user_activities: Track user interactions")
        print("- card_reviews: Track individual card reviews")
        print("- algorithm_performance: Track algorithm metrics")
        print("- analytics: Store daily statistics")

if __name__ == '__main__':
    print("Starting database migration...")
    upgrade_database()
    print("Database migration completed successfully!") 