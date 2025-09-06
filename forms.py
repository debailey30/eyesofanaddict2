from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, EmailField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class ContactForm(FlaskForm):
    """Contact form for community inquiries"""
    name = StringField('Name', validators=[
        DataRequired(message="Please enter your name"),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters")
    ])
    
    email = EmailField('Email', validators=[
        DataRequired(message="Please enter your email address"),
        Email(message="Please enter a valid email address")
    ])
    
    subject = StringField('Subject', validators=[
        DataRequired(message="Please enter a subject"),
        Length(min=5, max=200, message="Subject must be between 5 and 200 characters")
    ])
    
    message = TextAreaField('Message', validators=[
        DataRequired(message="Please enter your message"),
        Length(min=10, max=1000, message="Message must be between 10 and 1000 characters")
    ])
    
    submit = SubmitField('Send Message')

class EmailSubscriptionForm(FlaskForm):
    """Form for joining the email community"""
    name = StringField('Name (Optional)', validators=[
        Length(max=100, message="Name must be less than 100 characters")
    ])
    
    email = EmailField('Email Address', validators=[
        DataRequired(message="Please enter your email address"),
        Email(message="Please enter a valid email address")
    ])
    
    submit = SubmitField('Join Our Community')

class RegistrationForm(FlaskForm):
    """Form for user registration for journal subscription"""
    name = StringField('Full Name', validators=[
        DataRequired(message="Please enter your full name"),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters")
    ])
    
    email = EmailField('Email Address', validators=[
        DataRequired(message="Please enter your email address"),
        Email(message="Please enter a valid email address")
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message="Please enter a password"),
        Length(min=6, max=50, message="Password must be between 6 and 50 characters")
    ])
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    
    submit = SubmitField('Create Account & Subscribe')

class LoginForm(FlaskForm):
    """Form for user login"""
    email = EmailField('Email Address', validators=[
        DataRequired(message="Please enter your email address"),
        Email(message="Please enter a valid email address")
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message="Please enter your password")
    ])
    
    submit = SubmitField('Sign In')
