from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class EmailSubscriber(db.Model):
    """Model for storing email subscribers to the recovery community"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    subscribed_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    source = db.Column(db.String(50), default='website')  # Track where they subscribed from
    
    def __repr__(self):
        return f'<EmailSubscriber {self.email}>'

class ContactMessage(db.Model):
    """Model for storing contact form messages"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<ContactMessage from {self.email}: {self.subject}>'

class User(UserMixin, db.Model):
    """Model for user accounts with journal subscriptions"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_owner = db.Column(db.Boolean, default=False)  # Owner bypass subscription
    
    # Subscription details
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    subscription_status = db.Column(db.String(50), default='inactive')  # active, canceled, past_due
    subscription_start = db.Column(db.DateTime, nullable=True)
    subscription_end = db.Column(db.DateTime, nullable=True)
    
    # Recovery journal progress
    current_day = db.Column(db.Integer, default=1)
    days_completed = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_active_subscription(self):
        """Check if user has an active subscription"""
        return self.subscription_status == 'active' or self.is_owner
    
    def __repr__(self):
        return f'<User {self.email}>'

class JournalEntry(db.Model):
    """Model for individual journal entries with enhanced content storage"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)  # Day 1-30
    
    # Enhanced content fields for comprehensive journaling
    daily_reflection = db.Column(db.Text, nullable=True)  # Main reflection content
    gratitude_items = db.Column(db.Text, nullable=True)  # Gratitude list (JSON or text)
    challenges_faced = db.Column(db.Text, nullable=True)  # Daily challenges
    wins_celebrations = db.Column(db.Text, nullable=True)  # Daily wins/celebrations
    goals_tomorrow = db.Column(db.Text, nullable=True)  # Goals for next day
    mood_rating = db.Column(db.Integer, nullable=True)  # 1-10 scale
    energy_level = db.Column(db.Integer, nullable=True)  # 1-10 scale
    sleep_quality = db.Column(db.Integer, nullable=True)  # 1-10 scale
    trigger_notes = db.Column(db.Text, nullable=True)  # Trigger awareness notes
    coping_strategies = db.Column(db.Text, nullable=True)  # Strategies used today
    support_connections = db.Column(db.Text, nullable=True)  # People connected with
    drawing_data = db.Column(db.Text, nullable=True)  # Canvas drawing data as base64
    
    # Progress tracking
    completed = db.Column(db.Boolean, default=False)
    time_spent_minutes = db.Column(db.Integer, nullable=True)  # Time spent journaling
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('journal_entries', lazy=True))
    
    def get_completion_percentage(self):
        """Calculate how complete this journal entry is based on filled fields"""
        total_fields = 10  # Number of main content fields
        filled_fields = 0
        
        fields_to_check = [
            self.daily_reflection, self.gratitude_items, self.challenges_faced,
            self.wins_celebrations, self.goals_tomorrow, self.trigger_notes,
            self.coping_strategies, self.support_connections
        ]
        
        for field in fields_to_check:
            if field and field.strip():
                filled_fields += 1
        
        if self.mood_rating is not None:
            filled_fields += 1
        if self.energy_level is not None:
            filled_fields += 1
            
        return int((filled_fields / total_fields) * 100)
    
    def __repr__(self):
        return f'<JournalEntry Day {self.day_number} for User {self.user_id}>'

class PDFAnnotation(db.Model):
    """Model for PDF page annotations and drawings"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)  # Page 1-79
    notes = db.Column(db.Text, nullable=True)  # Text notes for this page
    drawing_data = db.Column(db.Text, nullable=True)  # Canvas drawing data as base64
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('pdf_annotations', lazy=True))
    
    def __repr__(self):
        return f'<PDFAnnotation Page {self.page_number} for User {self.user_id}>'

class SiteSettings(db.Model):
    """Model for customizable site layout and styling"""
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(50), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SiteSettings {self.setting_name}: {self.setting_value}>'