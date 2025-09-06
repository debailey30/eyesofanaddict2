from flask import render_template, request, flash, redirect, url_for
from app import app, db
from forms import ContactForm, EmailSubscriptionForm
from models import EmailSubscriber, ContactMessage
import logging

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
                flash(f"Welcome to the Eyes of an Addict community! You'll receive updates and recovery resources at {form.email.data}", 'success')
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

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return render_template('base.html', error_message="Internal server error"), 500
