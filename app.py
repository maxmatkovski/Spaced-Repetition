from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'flashcards.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

    def calculate(self, quality):
        if quality >= 3:
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.ease_factor)
            
            self.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            self.ease_factor = max(1.3, self.ease_factor)
            self.repetitions += 1
        else:
            self.interval = 1
            self.repetitions = 0
        
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

@app.route('/')
def index():
    return render_template('index.html')

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

    # Update review statistics
    if algorithm == 'sm2':
        card.sm2_total_reviews += 1
        if rating >= 3:  # Consider rating 3 and 4 as correct
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
    else:
        card.fsrs_total_reviews += 1
        if rating >= 3:  # Consider rating 3 and 4 as correct
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

if __name__ == '__main__':
    create_app()
    app.run(debug=True, host='localhost', port=3000) 