import os
import stripe
from flask import url_for
from datetime import datetime, timedelta

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def create_checkout_session(user_email, user_name):
    """Create a Stripe checkout session for journal subscription"""
    try:
        # Domain for redirects
        domain = os.environ.get('REPLIT_DEV_DOMAIN') if os.environ.get('REPLIT_DEPLOYMENT') else 'localhost:5000'
        protocol = 'https' if os.environ.get('REPLIT_DEPLOYMENT') else 'http'
        
        checkout_session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': '30-Day Recovery Journal - Premium Subscription',
                        'description': 'Interactive digital recovery journal with personal dashboard and progress tracking',
                        'images': []  # Add product images if you have them
                    },
                    'unit_amount': 1999,  # $19.99 in cents
                    'recurring': {
                        'interval': 'month',
                        'interval_count': 1,
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{protocol}://{domain}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{protocol}://{domain}/subscription/cancel',
            metadata={
                'user_email': user_email,
                'user_name': user_name
            },
            subscription_data={
                'metadata': {
                    'user_email': user_email,
                    'user_name': user_name
                }
            },
            billing_address_collection='required',
            automatic_tax={'enabled': True},
        )
        
        return checkout_session.url
    except Exception as e:
        print(f"Stripe checkout error: {e}")
        return None

def create_customer_portal_session(customer_id):
    """Create a customer portal session for subscription management"""
    try:
        domain = os.environ.get('REPLIT_DEV_DOMAIN') if os.environ.get('REPLIT_DEPLOYMENT') else 'localhost:5000'
        protocol = 'https' if os.environ.get('REPLIT_DEPLOYMENT') else 'http'
        
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f'{protocol}://{domain}/dashboard',
        )
        return portal_session.url
    except Exception as e:
        print(f"Customer portal error: {e}")
        return None

def get_subscription_status(customer_id):
    """Get the current subscription status for a customer"""
    try:
        subscriptions = stripe.Subscription.list(customer=customer_id, limit=1)
        if subscriptions.data:
            subscription = subscriptions.data[0]
            return {
                'status': subscription.status,
                'current_period_start': datetime.fromtimestamp(subscription.current_period_start),
                'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
                'cancel_at_period_end': subscription.cancel_at_period_end
            }
        return None
    except Exception as e:
        print(f"Subscription status error: {e}")
        return None

def cancel_subscription(customer_id):
    """Cancel a subscription at the end of the current period"""
    try:
        subscriptions = stripe.Subscription.list(customer=customer_id, limit=1)
        if subscriptions.data:
            subscription = subscriptions.data[0]
            updated_subscription = stripe.Subscription.modify(
                subscription.id,
                cancel_at_period_end=True
            )
            return True
        return False
    except Exception as e:
        print(f"Cancel subscription error: {e}")
        return False