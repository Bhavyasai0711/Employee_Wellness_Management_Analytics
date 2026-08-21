from textblob import TextBlob
from database import db
from Module5_MentalHealthAnalytics.models import SentimentLog

def analyze_mental_health_text(text, user):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    
    if polarity > 0.15:
        sentiment_label = "Positive"
    elif polarity < -0.15:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Neutral"
        
    text_lower = text.lower()
    
    burnout_keywords = ["exhausted", "tired", "burnout", "overworked", "dread", "pressure", "no break", "overwhelming", "collapse", "fatigue", "drained"]
    anxiety_keywords = ["anxious", "worried", "panic", "scared", "nervous", "stressed out", "heart racing", "fear", "uncomfortable", "agitated"]
    depression_keywords = ["sad", "hopeless", "depressed", "lonely", "unhappy", "cry", "giving up", "miserable", "despair"]
    
    burnout_hits = sum(1 for kw in burnout_keywords if kw in text_lower)
    anxiety_hits = sum(1 for kw in anxiety_keywords if kw in text_lower)
    depression_hits = sum(1 for kw in depression_keywords if kw in text_lower)
    
    if burnout_hits >= 2 or (burnout_hits >= 1 and polarity < -0.15):
        stress_category = "Burnout Warning"
    elif anxiety_hits >= 2 or (anxiety_hits >= 1 and polarity < -0.15):
        stress_category = "Anxiety Alert"
    elif depression_hits >= 1 or polarity < -0.35:
        stress_category = "Low Mood / Stress Warning"
    else:
        if polarity > 0.2:
            stress_category = "Stable & Positive"
        else:
            stress_category = "Stable"
            
    log_entry = SentimentLog(
        user_id=user.id,
        feedback_text=text,
        polarity=round(polarity, 3),
        subjectivity=round(subjectivity, 3),
        stress_category=stress_category,
        sentiment_label=sentiment_label
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return log_entry
