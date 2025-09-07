from flask import render_template, request, flash, redirect, url_for, session, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from forms import ContactForm, EmailSubscriptionForm, RegistrationForm, LoginForm
from models import EmailSubscriber, ContactMessage, User, JournalEntry, SiteSettings, PDFAnnotation
from email_service import send_welcome_email
from stripe_service import create_checkout_session, create_customer_portal_session, get_subscription_status
import stripe
import logging
import os
from datetime import datetime

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
    """User dashboard for recovery journal access"""
    # Check subscription status
    if not current_user.has_active_subscription():
        flash('Your subscription is not active. Please subscribe to access your recovery journal.', 'error')
        return redirect(url_for('subscription_info'))
    
    # Get user's basic progress tracking entries
    entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.day_number).all()
    
    # Create missing entries for days 1-30 for progress tracking
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
    
    # Get current layout settings for dynamic styling
    settings = {}
    for setting in SiteSettings.query.all():
        settings[setting.setting_name] = setting.setting_value
    
    return render_template('dashboard.html', entries=entries, current_user=current_user, settings=settings)

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

@app.route('/recovery-journal')
@login_required
def recovery_journal():
    """Interactive recovery journal interface"""
    # Check subscription status
    if not current_user.has_active_subscription():
        flash('Your subscription is not active. Please subscribe to access the recovery journal.', 'error')
        return redirect(url_for('subscription_info'))
    
    # Get the current day or default to day 1
    current_day = request.args.get('day', current_user.current_day, type=int)
    if current_day < 1 or current_day > 30:
        current_day = 1
    
    # Get or create journal entry for this day
    entry = JournalEntry.query.filter_by(user_id=current_user.id, day_number=current_day).first()
    if not entry:
        entry = JournalEntry(user_id=current_user.id, day_number=current_day)
        db.session.add(entry)
        db.session.commit()
    
    # Get all entries for progress overview
    all_entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.day_number).all()
    
    return render_template('interactive_journal.html', 
                         entry=entry, 
                         current_day=current_day, 
                         all_entries=all_entries,
                         current_user=current_user)

@app.route('/save-journal-entry', methods=['POST'])
@login_required
def save_journal_entry():
    """Save journal entry via AJAX"""
    if not current_user.has_active_subscription():
        return {'success': False, 'error': 'Subscription required'}, 403
    
    day_number = request.form.get('day_number', type=int)
    if not day_number or day_number < 1 or day_number > 30:
        return {'success': False, 'error': 'Invalid day number'}, 400
    
    # Get or create entry
    entry = JournalEntry.query.filter_by(user_id=current_user.id, day_number=day_number).first()
    if not entry:
        entry = JournalEntry(user_id=current_user.id, day_number=day_number)
        db.session.add(entry)
    
    # Update entry fields
    entry.daily_reflection = request.form.get('daily_reflection', '').strip()
    entry.gratitude_items = request.form.get('gratitude_items', '').strip()
    entry.challenges_faced = request.form.get('challenges_faced', '').strip()
    entry.wins_celebrations = request.form.get('wins_celebrations', '').strip()
    entry.goals_tomorrow = request.form.get('goals_tomorrow', '').strip()
    entry.trigger_notes = request.form.get('trigger_notes', '').strip()
    entry.coping_strategies = request.form.get('coping_strategies', '').strip()
    entry.support_connections = request.form.get('support_connections', '').strip()
    entry.drawing_data = request.form.get('drawing_data', '').strip()
    
    # Update ratings
    entry.mood_rating = request.form.get('mood_rating', type=int)
    entry.energy_level = request.form.get('energy_level', type=int)
    entry.sleep_quality = request.form.get('sleep_quality', type=int)
    
    # Mark as completed if significant content is present
    completion_percentage = entry.get_completion_percentage()
    entry.completed = completion_percentage >= 50  # Consider 50%+ as completed
    entry.updated_date = datetime.utcnow()
    
    try:
        db.session.commit()
        
        # Update user progress
        if entry.completed and current_user.current_day == day_number:
            current_user.current_day = min(day_number + 1, 30)
            current_user.days_completed = JournalEntry.query.filter_by(
                user_id=current_user.id, completed=True
            ).count()
            current_user.last_activity = datetime.utcnow()
            db.session.commit()
        
        return {
            'success': True, 
            'completion_percentage': completion_percentage,
            'is_completed': entry.completed,
            'message': 'Entry saved successfully!'
        }
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving journal entry: {e}")
        return {'success': False, 'error': 'Failed to save entry'}, 500

@app.route('/journal-pdf')
@login_required 
def journal_pdf():
    """Interactive PDF journal viewer with drawing and navigation"""
    # Check subscription status
    if not current_user.has_active_subscription():
        flash('Your subscription is not active. Please subscribe to access the recovery journal.', 'error')
        return redirect(url_for('subscription_info'))
    
    # Get current page from URL parameter
    current_page = request.args.get('page', 1, type=int)
    if current_page < 1 or current_page > 79:
        current_page = 1
    
    # Get or create PDF annotation entry for this page
    pdf_entry = PDFAnnotation.query.filter_by(
        user_id=current_user.id, 
        page_number=current_page
    ).first()
    if not pdf_entry:
        pdf_entry = PDFAnnotation(user_id=current_user.id, page_number=current_page)
        db.session.add(pdf_entry)
        db.session.commit()
    
    return render_template('pdf_journal.html', 
                         current_page=current_page, 
                         total_pages=79,
                         pdf_entry=pdf_entry,
                         current_user=current_user)

@app.route('/journal-pdf-download')
@login_required 
def journal_pdf_download():
    """Download the full 79-page PDF journal guide"""
    # Check subscription status
    if not current_user.has_active_subscription():
        flash('Your subscription is not active. Please subscribe to access the recovery journal.', 'error')
        return redirect(url_for('subscription_info'))
    
    # Serve the professional 79-page recovery journal as download
    return send_from_directory('static/downloads', 'recovery-journal-full.pdf', as_attachment=True)

@app.route('/save-pdf-annotation', methods=['POST'])
@login_required
def save_pdf_annotation():
    """Save PDF page annotation via AJAX"""
    if not current_user.has_active_subscription():
        return {'success': False, 'error': 'Subscription required'}, 403
    
    page_number = request.form.get('page_number', type=int)
    if not page_number or page_number < 1 or page_number > 79:
        return {'success': False, 'error': 'Invalid page number'}, 400
    
    # Get or create annotation entry
    annotation = PDFAnnotation.query.filter_by(
        user_id=current_user.id, 
        page_number=page_number
    ).first()
    if not annotation:
        annotation = PDFAnnotation(user_id=current_user.id, page_number=page_number)
        db.session.add(annotation)
    
    # Update annotation fields
    annotation.notes = request.form.get('notes', '').strip()
    annotation.drawing_data = request.form.get('drawing_data', '').strip()
    annotation.updated_date = datetime.utcnow()
    
    try:
        db.session.commit()
        return {
            'success': True,
            'message': 'Annotation saved successfully!'
        }
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving PDF annotation: {e}")
        return {'success': False, 'error': 'Failed to save annotation'}, 500

@app.route('/admin/layout')
@login_required
def admin_layout():
    """Admin interface for layout customization (owner only)"""
    if not current_user.is_owner:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get current settings
    settings = {}
    for setting in SiteSettings.query.all():
        settings[setting.setting_name] = setting.setting_value
    
    return render_template('admin_layout.html', settings=settings)

@app.route('/admin/layout/update', methods=['POST'])
@login_required
def update_layout():
    """Update layout settings (owner only)"""
    if not current_user.is_owner:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Update or create settings
    layout_settings = {
        'primary_color': request.form.get('primary_color', '#2E8B57'),
        'secondary_color': request.form.get('secondary_color', '#4169E1'),
        'accent_color': request.form.get('accent_color', '#9370DB'),
        'dashboard_layout': request.form.get('dashboard_layout', 'grid'),
        'font_size': request.form.get('font_size', 'medium'),
        'card_style': request.form.get('card_style', 'modern'),
        'spacing': request.form.get('spacing', 'normal')
    }
    
    for setting_name, setting_value in layout_settings.items():
        existing_setting = SiteSettings.query.filter_by(setting_name=setting_name).first()
        if existing_setting:
            existing_setting.setting_value = setting_value
            existing_setting.updated_date = datetime.utcnow()
        else:
            new_setting = SiteSettings(
                setting_name=setting_name,
                setting_value=setting_value,
                description=f"Layout setting for {setting_name}"
            )
            db.session.add(new_setting)
    
    try:
        db.session.commit()
        flash('Layout settings updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating layout settings: {e}")
        flash('Error updating settings. Please try again.', 'error')
    
    return redirect(url_for('admin_layout'))

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
        
        # Initialize default settings
        default_settings = [
            ('primary_color', '#2E8B57', 'Primary brand color'),
            ('secondary_color', '#4169E1', 'Secondary brand color'),
            ('accent_color', '#9370DB', 'Accent color for highlights'),
            ('dashboard_layout', 'grid', 'Dashboard layout style'),
            ('font_size', 'medium', 'Default font size'),
            ('card_style', 'modern', 'Card design style'),
            ('spacing', 'normal', 'Element spacing')
        ]
        
        for name, value, desc in default_settings:
            setting = SiteSettings(setting_name=name, setting_value=value, description=desc)
            db.session.add(setting)
        
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
