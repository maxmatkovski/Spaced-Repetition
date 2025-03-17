# Spaced Repetition Algorithm Comparison Platform

A modern web application for comparing and analyzing the effectiveness of different spaced repetition algorithms, specifically SM2 (SuperMemo 2) and FSRS (Free Spaced Repetition Scheduler).

## Table of Contents
- [Introduction](#introduction)
- [History of Spaced Repetition](#history-of-spaced-repetition)
- [Market Analysis](#market-analysis)
- [Algorithm Comparison](#algorithm-comparison)
- [Technical Implementation](#technical-implementation)
- [Installation](#installation)
- [Deployment](#deployment)
- [Usage](#usage)
- [Future Development](#future-development)

## Introduction

This platform provides a real-time comparison between two prominent spaced repetition algorithms: SM2 and FSRS. Users can test both algorithms simultaneously, track performance metrics, and understand which approach better suits their learning style.

## History of Spaced Repetition

### Origins
- **1885**: Hermann Ebbinghaus discovers the "forgetting curve" and "spacing effect"
- **1932**: Cecil Alec Mace conducts first empirical studies on spaced repetition
- **1967**: Sebastian Leitner develops the "Leitner system" for flashcards
- **1985**: Piotr Woźniak creates SuperMemo and the SM2 algorithm
- **2022**: Open-source FSRS algorithm is developed as a modern alternative

### Evolution of Algorithms

#### Early Methods
- Manual spacing systems (Leitner boxes)
- Fixed interval repetition
- Gradual refinement through empirical testing

#### Modern Developments
- Computer-assisted scheduling
- Machine learning optimization
- Personalized interval adjustments
- Neural network integration

## Market Analysis

### Current Market Size
- Global EdTech market: $342.9 billion (2023)
- Projected growth to $519.7 billion by 2027
- Spaced repetition apps segment: $2.4 billion (2023)

### Key Market Segments
1. **Language Learning**
   - Market Size: $17.7 billion (2023)
   - Key Players: Duolingo, Anki, Memrise
   - Growth Rate: 18% CAGR

2. **Professional Education**
   - Market Size: $25.3 billion (2023)
   - Applications: Medical, Legal, Technical
   - Growth Rate: 15% CAGR

3. **Academic Education**
   - Market Size: $12.1 billion (2023)
   - Focus: K-12, Higher Education
   - Growth Rate: 12% CAGR

### Startup Opportunity

#### Value Proposition
Custom Learning Algorithm Platform (CLAP) - A SaaS solution that:
1. Creates personalized spaced repetition algorithms
2. Adapts to individual learning patterns
3. Optimizes retention through machine learning
4. Provides analytics and insights

#### Target Markets
1. **Enterprise Learning & Development**
   - Corporate training programs
   - Professional certification
   - Compliance training

2. **Educational Institutions**
   - Universities
   - Online learning platforms
   - Language schools

3. **Individual Learners**
   - Students
   - Lifelong learners
   - Professional development

#### Revenue Model
1. **B2B SaaS Subscriptions**
   - Enterprise licensing
   - API access
   - Custom algorithm development

2. **B2C Premium Features**
   - Advanced analytics
   - Algorithm customization
   - Cross-platform sync

## Algorithm Comparison

### SM2 (SuperMemo 2)
```python
Characteristics:
- Fixed intervals based on performance
- Ease factor adjustment
- Simple implementation
- Proven track record

Advantages:
- Easy to understand and implement
- Computationally efficient
- Reliable for consistent learners

Limitations:
- Less adaptive to individual patterns
- Fixed interval progression
- Limited personalization
```

### FSRS (Free Spaced Repetition Scheduler)
```python
Characteristics:
- Dynamic difficulty adjustment
- Stability-based intervals
- Machine learning optimization
- Modern implementation

Advantages:
- Highly adaptive
- Better handling of varied learning patterns
- More sophisticated interval calculations

Limitations:
- More complex implementation
- Higher computational requirements
- Requires more data for optimization
```

## Technical Implementation

### Features
- Real-time algorithm comparison
- Performance analytics
- Interactive flashcard interface
- Progress tracking
- Statistical analysis

### Technology Stack
- Backend: Flask/Python
- Database: SQLAlchemy
- Frontend: Tailwind CSS
- Deployment: Render.com

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/spaced-repetition-comparison.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

## Deployment

### Prerequisites
1. A GitHub account
2. A Render.com account (free tier available)
3. Your application code pushed to a GitHub repository

### Automatic Deployments
- Every push to the main branch triggers an automatic deployment
- Changes typically go live within 5-10 minutes
- You can monitor deployments in the Render dashboard
- Deploy logs are available in real-time

### Step 1: Prepare Your Repository
1. Create a new GitHub repository
2. Initialize git in your local project (if not already done):
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/your-repo-name.git
git push -u origin main
```

### Step 2: Deploy to Render.com
1. Log in to [Render.com](https://render.com)
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure the web service:
   - Name: `your-app-name`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Plan: `Free`

### Step 3: Configure Environment Variables
Add the following environment variables in Render's dashboard:
- `SECRET_KEY`: A secure random string (e.g., output of `python -c "import secrets; print(secrets.token_hex(16))"`)
- `DATABASE_URL`: Will be auto-configured if using Render's PostgreSQL (optional)

### Step 4: Database Setup (Optional)
1. Create a new PostgreSQL database in Render:
   - Go to "New +" → "PostgreSQL"
   - Choose the free tier
   - Note the Internal Database URL
2. Add the Internal Database URL to your web service's environment variables

### Step 5: Verify Deployment
1. Wait for the initial deploy to complete (5-10 minutes)
2. Your app will be available at `https://your-app-name.onrender.com`
3. Monitor the deployment logs for any issues

### Common Issues and Solutions
1. **Application Error**:
   - Check deployment logs in Render dashboard
   - Verify environment variables are set correctly
   - Ensure `requirements.txt` includes all dependencies

2. **Database Connection Issues**:
   - Verify `DATABASE_URL` is set correctly
   - Check database credentials
   - Ensure database migrations are running

3. **Static Files Not Loading**:
   - Verify static files are properly configured in Flask
   - Check file permissions
   - Clear browser cache

## Usage

1. Access the web interface at http://localhost:8000
2. Review cards using both algorithms simultaneously
3. Rate your recall from 1 (Again) to 4 (Easy)
4. Track and compare algorithm performance
5. Use the Reset button to start fresh
6. Make all cards due to review again

## Future Development

### Planned Features
1. **Algorithm Enhancement**
   - Neural network integration
   - Personalized parameter tuning
   - Multi-factor optimization

2. **Platform Expansion**
   - Mobile applications
   - API access
   - Enterprise features

3. **Analytics**
   - Machine learning insights
   - Performance prediction
   - Learning pattern analysis

### Research Opportunities
1. Novel algorithm development
2. Learning pattern analysis
3. Cognitive load optimization
4. Cross-disciplinary applications

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
