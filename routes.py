from flask import render_template, request, flash, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from forms import ContactForm, EmailSubscriptionForm, RegistrationForm, LoginForm
from models import EmailSubscriber, ContactMessage, User, JournalEntry
from email_service import send_welcome_email
from stripe_service import create_checkout_session, create_customer_portal_session, get_subscription_status
import stripe
import logging
import os

@app.route('/')
def index():
    """Main homepage with hero section and overview"""
    return render_template('index.html')

@app.route('/products')
def products():
    """Product showcase page for digital and POD items"""
    return render_template('products.html')

@app.route('/faq')
def faq():
    """FAQ page with common questions"""
    return render_template('faq.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page with form for community inquiries"""
    form = ContactForm()
    
    if form.validate_on_submit():
        # Save contact message to database
        contact_msg = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data
        )
        
        try:
            db.session.add(contact_msg)
            db.session.commit()
            logging.info(f"Contact form submitted: {form.name.data} ({form.email.data}) - {form.subject.data}")
            flash(f"Thank you {form.name.data}! Your message has been received. We'll get back to you soon.", 'success')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error saving contact message: {e}")
            flash("There was an error sending your message. Please try again.", 'error')
        
        return redirect(url_for('contact'))
    
    return render_template('contact.html', form=form)

@app.route('/join', methods=['GET', 'POST'])
def join_community():
    """Email subscription page for joining the recovery community"""
    form = EmailSubscriptionForm()
    
    if form.validate_on_submit():
        # Check if email already exists
        existing_subscriber = EmailSubscriber.query.filter_by(email=form.email.data).first()
        
        if existing_subscriber:
            if existing_subscriber.is_active:
                flash("You're already part of our community! Thanks for your continued support.", 'info')
            else:
                # Reactivate the subscription
                existing_subscriber.is_active = True
                existing_subscriber.name = form.name.data if form.name.data else existing_subscriber.name
                db.session.commit()
                
                # Send welcome email for returning subscriber
                email_sent = send_welcome_email(form.email.data, form.name.data)
                
                if email_sent:
                    flash("Welcome back! Your subscription has been reactivated and fresh recovery resources are on their way to your inbox!", 'success')
                else:
                    flash("Welcome back! Your subscription has been reactivated.", 'success')
        else:
            # Create new subscriber
            subscriber = EmailSubscriber(
                email=form.email.data,
                name=form.name.data if form.name.data else None,
                source='website_join'
            )
            
            try:
                db.session.add(subscriber)
                db.session.commit()
                logging.info(f"New email subscriber: {form.email.data}")
                
                # Send welcome email with resources
                email_sent = send_welcome_email(form.email.data, form.name.data)
                
                if email_sent:
                    flash(f"Welcome to the Eyes of an Addict community! Check your email at {form.email.data} for your free recovery resources!", 'success')
                else:
                    flash(f"You've joined our community! We're working on getting your welcome email to you - please check back if you don't receive it soon.", 'success')
                    
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error saving email subscriber: {e}")
                flash("There was an error joining the community. Please try again.", 'error')
        
        return redirect(url_for('join_community'))
    
    return render_template('join.html', form=form)

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('base.html', error_message="Page not found"), 404

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration for journal subscription"""
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('An account with this email already exists. Please log in instead.', 'error')
            return redirect(url_for('login'))
        
        # Create new user
        user = User(
            email=form.email.data,
            name=form.name.data
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Log in the user
            login_user(user)
            
            # Create Stripe checkout session
            checkout_url = create_checkout_session(user.email, user.name)
            if checkout_url:
                return redirect(checkout_url)
            else:
                flash('Error creating checkout session. Please try again.', 'error')
                return redirect(url_for('register'))
                
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating user: {e}")
            flash('Error creating account. Please try again.', 'error')
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            
            # Redirect to dashboard or intended page
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard for journal access"""
    # Check subscription status
    if not current_user.has_active_subscription():
        flash('Your subscription is not active. Please subscribe to access your recovery journal.', 'error')
        return redirect(url_for('subscription_info'))
    
    # Get user's journal entries
    entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.day_number).all()
    
    # Create missing entries for days 1-30
    existing_days = {entry.day_number for entry in entries}
    for day in range(1, 31):
        if day not in existing_days:
            new_entry = JournalEntry(user_id=current_user.id, day_number=day)
            db.session.add(new_entry)
    
    try:
        db.session.commit()
        entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.day_number).all()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating journal entries: {e}")
    
    return render_template('dashboard.html', entries=entries, current_user=current_user)

@app.route('/subscription/success')
def subscription_success():
    """Handle successful Stripe subscription"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            # Retrieve the session from Stripe
            stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                # Update user subscription status
                user_email = session.metadata.get('user_email')
                user = User.query.filter_by(email=user_email).first()
                
                if user:
                    user.stripe_customer_id = session.customer
                    user.subscription_status = 'active'
                    db.session.commit()
                    
                    flash('Welcome to your Recovery Journal! Your subscription is now active.', 'success')
                    return redirect(url_for('dashboard'))
        except Exception as e:
            logging.error(f"Error processing subscription success: {e}")
    
    flash('There was an issue processing your subscription. Please contact support.', 'error')
    return redirect(url_for('index'))

@app.route('/subscription/cancel')
def subscription_cancel():
    """Handle cancelled Stripe subscription"""
    flash('Subscription cancelled. You can try again anytime.', 'info')
    return redirect(url_for('index'))

@app.route('/subscription/manage')
@login_required
def manage_subscription():
    """Redirect to Stripe customer portal"""
    if current_user.stripe_customer_id:
        portal_url = create_customer_portal_session(current_user.stripe_customer_id)
        if portal_url:
            return redirect(portal_url)
    
    flash('Unable to access subscription management. Please contact support.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/subscription/info')
def subscription_info():
    """Information about journal subscription"""
    return render_template('subscription_info.html')

@app.route('/create-owner-account')
def create_owner_account():
    """Create owner account for site access"""
    # Check if owner already exists
    existing_owner = User.query.filter_by(is_owner=True).first()
    if existing_owner:
        return f"Owner account already exists for {existing_owner.email}"
    
    # Create owner account
    owner = User(
        email='owner@eyesofanaddict.online',
        name='D. Bailey',
        is_owner=True,
        subscription_status='active'  # Set as active for full access
    )
    owner.set_password('recovery2024')  # Simple password for testing
    
    try:
        db.session.add(owner)
        db.session.commit()
        return f"Owner account created! Email: owner@eyesofanaddict.online | Password: recovery2024"
    except Exception as e:
        db.session.rollback()
        return f"Error creating owner account: {e}"

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('base.html', error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return render_template('base.html', error_message="Internal server error"), 500
