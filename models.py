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
    """Model for individual journal entries"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)  # Day 1-30
    content = db.Column(db.Text, nullable=True)
    mood_rating = db.Column(db.Integer, nullable=True)  # 1-10 scale
    completed = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('journal_entries', lazy=True))
    
    def __repr__(self):
        return f'<JournalEntry Day {self.day_number} for User {self.user_id}>'

class SiteSettings(db.Model):
    """Model for customizable site layout and styling"""
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(50), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SiteSettings {self.setting_name}: {self.setting_value}>'