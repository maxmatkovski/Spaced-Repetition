from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import os
import logging
import uuid
from models import db, UserActivity, CardReview, AlgorithmPerformance, Analytics

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Use environment variable for database URL in production
database_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'flashcards.db'))
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')

# Ensure the template directory exists
template_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
if not os.path.exists(template_dir):
    os.makedirs(template_dir)

db.init_app(app)

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    front = db.Column(db.String(500), nullable=False)
    back = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # SM2 fields
    sm2_interval = db.Column(db.Integer, default=0)
    sm2_repetitions = db.Column(db.Integer, default=0)
    sm2_ease_factor = db.Column(db.Float, default=2.5)
    sm2_next_review = db.Column(db.DateTime, default=datetime.utcnow)
    sm2_total_reviews = db.Column(db.Integer, default=0)
    sm2_correct_reviews = db.Column(db.Integer, default=0)
    
    # FSRS fields
    fsrs_difficulty = db.Column(db.Float, default=5.0)
    fsrs_stability = db.Column(db.Float, default=2.0)
    fsrs_next_review = db.Column(db.DateTime, default=datetime.utcnow)
    fsrs_total_reviews = db.Column(db.Integer, default=0)
    fsrs_correct_reviews = db.Column(db.Integer, default=0)

class SM2:
    def __init__(self):
        self.interval = 0
        self.repetitions = 0
        self.ease_factor = 2.5
        self.max_interval = 365  # Maximum interval of 1 year

    def calculate(self, quality):
        if quality >= 3:
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 6
            else:
                self.interval = min(round(self.interval * self.ease_factor), self.max_interval)
            
            self.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            self.ease_factor = max(1.3, min(2.5, self.ease_factor))  # Cap ease factor between 1.3 and 2.5
            self.repetitions += 1
        else:
            self.interval = 1
            self.repetitions = 0
            self.ease_factor = max(1.3, self.ease_factor - 0.2)  # Decrease ease factor on failure
        
        return self.interval, self.repetitions, self.ease_factor

class FSRS:
    def __init__(self):
        self.w = {
            0: 0.40255, 1: 1.18385, 2: 3.173, 3: 15.69105, 4: 7.1949, 5: 0.5345,
            6: 1.4604, 7: 0.0046, 8: 1.54575, 9: 0.1192, 10: 1.01925, 11: 1.9395,
            12: 0.11, 13: 0.29605, 14: 2.2698, 15: 0.2315, 16: 2.9898, 17: 0.51655, 18: 0.6621
        }
        self.decay = -0.5
        self.factor = 19/81
        self.min_difficulty = 1
        self.max_difficulty = 10

    def retrievability(self, t, s):
        return pow(1 + self.factor * t / s, self.decay)

    def difficulty(self, d, rating):
        return max(self.min_difficulty, min(self.max_difficulty, d + self.w[0] * (3 - rating)))

    def stability(self, s, d, r, rating):
        hard = 1 if rating == 2 else 0
        easy = 1 if rating == 4 else 0
        new_s = s * (1 + pow(2.718281828, self.w[1]) * (11 - d) * pow(s, -self.w[2]) * 
                     (pow(2.718281828, (1 - r) * self.w[3]) - 1) * self.w[4] / (1 + self.w[5] * hard) * 
                     (1 + self.w[6] * easy))
        return max(0.1, new_s)

    def next_interval(self, s):
        return int(s * 9 / self.factor)

    def calculate(self, difficulty, stability, last_review, now, rating):
        elapsed = (now - last_review).days
        r = self.retrievability(elapsed, stability)
        new_d = self.difficulty(difficulty, rating)
        new_s = self.stability(stability, difficulty, r, rating)
        next_interval = self.next_interval(new_s)
        return new_d, new_s, next_interval

def create_app():
    with app.app_context():
        db.create_all()
        # Check if we already have cards
        card_count = Card.query.count()
        logger.info(f"Found {card_count} existing cards")
        if card_count == 0:
            create_test_cards()
    return app

def track_user_activity(action):
    """Track user activity with session management"""
    session_id = request.cookies.get('session_id', str(uuid.uuid4()))
    activity = UserActivity(
        session_id=session_id,
        action=action,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(activity)
    db.session.commit()
    return session_id

def update_analytics(session_id, algorithm=None, rating=None):
    """Update daily analytics"""
    today = datetime.utcnow().date()
    analytics = Analytics.query.filter_by(date=today).first()
    
    if not analytics:
        analytics = Analytics(
            date=today,
            total_reviews=0,
            unique_sessions=0,
            daily_stats={'sm2_reviews': 0, 'fsrs_reviews': 0}
        )
        db.session.add(analytics)
    
    analytics.total_reviews += 1
    if algorithm:
        analytics.daily_stats[f'{algorithm}_reviews'] += 1
    
    # Update retention rates
    if rating and rating >= 3:
        if algorithm == 'sm2':
            analytics.avg_retention_sm2 = (
                (analytics.avg_retention_sm2 or 0) * analytics.daily_stats['sm2_reviews'] + 100
            ) / (analytics.daily_stats['sm2_reviews'] + 1)
        elif algorithm == 'fsrs':
            analytics.avg_retention_fsrs = (
                (analytics.avg_retention_fsrs or 0) * analytics.daily_stats['fsrs_reviews'] + 100
            ) / (analytics.daily_stats['fsrs_reviews'] + 1)
    
    db.session.commit()

@app.route('/')
def index():
    try:
        session_id = track_user_activity('page_view')
        response = make_response(render_template('index.html'))
        response.set_cookie('session_id', session_id, max_age=86400)  # 24 hours
        return response
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/add_card', methods=['POST'])
def add_card():
    data = request.json
    card = Card(
        front=data['front'],
        back=data['back']
    )
    db.session.add(card)
    db.session.commit()
    return jsonify({'message': 'Card added successfully', 'id': card.id})

@app.route('/get_due_cards')
def get_due_cards():
    algorithm = request.args.get('algorithm', 'sm2')
    now = datetime.utcnow()
    
    if algorithm == 'sm2':
        cards = Card.query.filter(Card.sm2_next_review <= now).all()
    else:
        cards = Card.query.filter(Card.fsrs_next_review <= now).all()
    
    # Log the number of cards found
    logger.info(f"Found {len(cards)} cards due for review with {algorithm} algorithm")
    
    # If no cards are due, return all cards
    if not cards:
        cards = Card.query.all()
        logger.info(f"No cards due, returning all {len(cards)} cards")
    
    return jsonify([{
        'id': card.id,
        'front': card.front,
        'back': card.back
    } for card in cards])

@app.route('/review_card', methods=['POST'])
def review_card():
    data = request.json
    card = Card.query.get(data['card_id'])
    rating = data['rating']
    algorithm = data['algorithm']
    now = datetime.utcnow()
    session_id = request.cookies.get('session_id', str(uuid.uuid4()))
    
    # Track the review
    review = CardReview(
        session_id=session_id,
        card_id=card.id,
        algorithm=algorithm,
        rating=rating,
        previous_interval=card.sm2_interval if algorithm == 'sm2' else card.fsrs_stability,
        review_time=data.get('review_time', 0)
    )
    
    # Update card and get new intervals
    if algorithm == 'sm2':
        card.sm2_total_reviews += 1
        if rating >= 3:
            card.sm2_correct_reviews += 1
        
        sm2 = SM2()
        sm2.interval = card.sm2_interval
        sm2.repetitions = card.sm2_repetitions
        sm2.ease_factor = card.sm2_ease_factor
        
        interval, repetitions, ease_factor = sm2.calculate(rating)
        
        card.sm2_interval = interval
        card.sm2_repetitions = repetitions
        card.sm2_ease_factor = ease_factor
        card.sm2_next_review = now + timedelta(days=interval)
        review.new_interval = interval
    else:
        card.fsrs_total_reviews += 1
        if rating >= 3:
            card.fsrs_correct_reviews += 1
            
        fsrs = FSRS()
        new_d, new_s, next_interval = fsrs.calculate(
            card.fsrs_difficulty,
            card.fsrs_stability,
            card.fsrs_next_review,
            now,
            rating
        )
        
        card.fsrs_difficulty = new_d
        card.fsrs_stability = new_s
        card.fsrs_next_review = now + timedelta(days=next_interval)
        review.new_interval = next_interval

    # Save review and update analytics
    db.session.add(review)
    update_analytics(session_id, algorithm, rating)
    db.session.commit()

    # Track algorithm performance
    perf = AlgorithmPerformance(
        session_id=session_id,
        algorithm=algorithm,
        metrics={
            'rating': rating,
            'interval_change': review.new_interval - review.previous_interval,
            'review_time': review.review_time
        }
    )
    db.session.add(perf)
    db.session.commit()

    return jsonify({'message': 'Review recorded successfully'})

@app.route('/statistics')
def get_statistics():
    cards = Card.query.all()
    stats = {
        'sm2': {
            'total_reviews': sum(card.sm2_total_reviews for card in cards),
            'correct_reviews': sum(card.sm2_correct_reviews for card in cards),
            'accuracy': 0,
            'average_interval': sum(card.sm2_interval for card in cards) / len(cards) if cards else 0
        },
        'fsrs': {
            'total_reviews': sum(card.fsrs_total_reviews for card in cards),
            'correct_reviews': sum(card.fsrs_correct_reviews for card in cards),
            'accuracy': 0,
            'average_stability': sum(card.fsrs_stability for card in cards) / len(cards) if cards else 0
        }
    }
    
    if stats['sm2']['total_reviews'] > 0:
        stats['sm2']['accuracy'] = (stats['sm2']['correct_reviews'] / stats['sm2']['total_reviews']) * 100
        
    if stats['fsrs']['total_reviews'] > 0:
        stats['fsrs']['accuracy'] = (stats['fsrs']['correct_reviews'] / stats['fsrs']['total_reviews']) * 100
    
    return jsonify(stats)

@app.route('/reset', methods=['POST'])
def reset_cards():
    try:
        # Delete all existing cards
        Card.query.delete()
        db.session.commit()
        
        # Create new test cards
        create_test_cards()
        
        return jsonify({'message': 'Cards reset successfully'})
    except Exception as e:
        logger.error(f"Error resetting cards: {str(e)}")
        return jsonify({'error': 'Failed to reset cards'}), 500

@app.route('/upgrade_all', methods=['POST'])
def upgrade_all():
    try:
        cards = Card.query.all()
        now = datetime.utcnow()
        
        for card in cards:
            # Move all cards to be due now
            card.sm2_next_review = now
            card.fsrs_next_review = now
        
        db.session.commit()
        return jsonify({'message': 'All cards upgraded to be due now'})
    except Exception as e:
        logger.error(f"Error upgrading cards: {str(e)}")
        return jsonify({'error': 'Failed to upgrade cards'}), 500

@app.route('/deck_status')
def deck_status():
    now = datetime.utcnow()
    sm2_due = Card.query.filter(Card.sm2_next_review <= now).count()
    fsrs_due = Card.query.filter(Card.fsrs_next_review <= now).count()
    
    cards = Card.query.all()
    stats = {
        'sm2': {
            'total_reviews': sum(card.sm2_total_reviews for card in cards),
            'correct_reviews': sum(card.sm2_correct_reviews for card in cards),
            'accuracy': 0,
            'average_interval': sum(card.sm2_interval for card in cards) / len(cards) if cards else 0
        },
        'fsrs': {
            'total_reviews': sum(card.fsrs_total_reviews for card in cards),
            'correct_reviews': sum(card.fsrs_correct_reviews for card in cards),
            'accuracy': 0,
            'average_stability': sum(card.fsrs_stability for card in cards) / len(cards) if cards else 0
        }
    }
    
    if stats['sm2']['total_reviews'] > 0:
        stats['sm2']['accuracy'] = (stats['sm2']['correct_reviews'] / stats['sm2']['total_reviews']) * 100
    if stats['fsrs']['total_reviews'] > 0:
        stats['fsrs']['accuracy'] = (stats['fsrs']['correct_reviews'] / stats['fsrs']['total_reviews']) * 100
    
    comparison = ""
    if stats['sm2']['total_reviews'] > 0 and stats['fsrs']['total_reviews'] > 0:
        if stats['sm2']['accuracy'] > stats['fsrs']['accuracy']:
            comparison = "SM2 is currently performing better with higher accuracy. It's a simpler algorithm that works well for consistent study habits."
        elif stats['fsrs']['accuracy'] > stats['sm2']['accuracy']:
            comparison = "FSRS is currently performing better with higher accuracy. It's more adaptive to your learning patterns."
        else:
            comparison = "Both algorithms are performing equally well. Choose based on your preference for review intervals."
    
    return jsonify({
        'sm2_due': sm2_due,
        'fsrs_due': fsrs_due,
        'comparison': comparison
    })

def create_test_cards():
    test_words = [
        ('ubiquitous', 'present, appearing, or found everywhere'),
        ('ephemeral', 'lasting for a very short time'),
        ('serendipity', 'the occurrence and development of events by chance in a happy or beneficial way'),
        ('paradigm', 'a typical example or pattern of something'),
        ('enigmatic', 'difficult to interpret or understand'),
        ('resilient', 'able to withstand or recover quickly from difficult conditions'),
        ('cognizant', 'having knowledge or awareness'),
        ('arbitrary', 'based on random choice or personal whim'),
        ('pragmatic', 'dealing with things sensibly and realistically'),
        ('ambivalent', 'having mixed feelings or contradictory ideas')
    ]
    
    logger.info("Creating test cards...")
    for front, back in test_words:
        card = Card(front=front, back=back)
        db.session.add(card)
        logger.info(f"Added card: {front}")
    
    db.session.commit()
    logger.info("Test cards created successfully")

# Add a route to serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/analytics')
def get_analytics():
    """Get detailed analytics data"""
    try:
        # Get date range
        days = int(request.args.get('days', 7))
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get analytics data
        analytics_data = Analytics.query.filter(
            Analytics.date >= start_date,
            Analytics.date <= end_date
        ).all()
        
        # Prepare response data
        response = {
            'daily_stats': [],
            'algorithm_comparison': {
                'sm2': {'total_reviews': 0, 'avg_retention': 0},
                'fsrs': {'total_reviews': 0, 'avg_retention': 0}
            },
            'user_engagement': {
                'total_unique_sessions': len(set(UserActivity.query.with_entities(UserActivity.session_id).all())),
                'total_reviews': sum(a.total_reviews for a in analytics_data)
            }
        }
        
        # Process daily stats
        for analytic in analytics_data:
            response['daily_stats'].append({
                'date': analytic.date.isoformat(),
                'total_reviews': analytic.total_reviews,
                'sm2_reviews': analytic.daily_stats.get('sm2_reviews', 0),
                'fsrs_reviews': analytic.daily_stats.get('fsrs_reviews', 0),
                'sm2_retention': analytic.avg_retention_sm2 or 0,
                'fsrs_retention': analytic.avg_retention_fsrs or 0
            })
            
            # Update algorithm totals
            response['algorithm_comparison']['sm2']['total_reviews'] += analytic.daily_stats.get('sm2_reviews', 0)
            response['algorithm_comparison']['fsrs']['total_reviews'] += analytic.daily_stats.get('fsrs_reviews', 0)
        
        # Calculate averages
        if response['algorithm_comparison']['sm2']['total_reviews'] > 0:
            response['algorithm_comparison']['sm2']['avg_retention'] = sum(
                d['sm2_retention'] * d['sm2_reviews'] for d in response['daily_stats']
            ) / response['algorithm_comparison']['sm2']['total_reviews']
            
        if response['algorithm_comparison']['fsrs']['total_reviews'] > 0:
            response['algorithm_comparison']['fsrs']['avg_retention'] = sum(
                d['fsrs_retention'] * d['fsrs_reviews'] for d in response['daily_stats']
            ) / response['algorithm_comparison']['fsrs']['total_reviews']
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

def init_db():
    with app.app_context():
        db.create_all()
        # Check if we already have cards
        card_count = Card.query.count()
        logger.info(f"Found {card_count} existing cards")
        if card_count == 0:
            create_test_cards()

if __name__ == '__main__':
    init_db()
    # Only use debug mode in development
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port) 