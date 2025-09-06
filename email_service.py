import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
import base64
import logging

def send_welcome_email(to_email, subscriber_name=None):
    """
    Send welcome email with recovery resources to new subscribers
    """
    try:
        # Get SendGrid API key
        sendgrid_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_key:
            logging.error("SENDGRID_API_KEY environment variable not set")
            return False

        sg = SendGridAPIClient(sendgrid_key)

        # Email content
        from_email = Email("info@eyesofanaddict.online", "D. Bailey - Eyes of an Addict")
        to_email = To(to_email)
        
        subject = "Welcome to Eyes of an Addict Recovery Community! 🌟"
        
        # Personalized greeting
        greeting = f"Hi {subscriber_name}," if subscriber_name else "Hi there,"
        
        # HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #2c3e50; max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #4a90e2 0%, #27ae60 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .highlight {{ background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .resources {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background-color: #2c3e50; color: white; padding: 15px; text-align: center; font-size: 14px; }}
                .button {{ background-color: #27ae60; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
                ul {{ padding-left: 20px; }}
                li {{ margin: 8px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🌟 Welcome to Eyes of an Addict!</h1>
                <p>Your recovery community is here to support you</p>
            </div>
            
            <div class="content">
                <p>{greeting}</p>
                
                <p>Thank you for joining the <strong>Eyes of an Addict</strong> recovery community! I'm D. Bailey, a Certified Peer Recovery Support Specialist with over 5 years in recovery, and I'm excited to support you on this journey.</p>
                
                <div class="highlight">
                    <h3>🎁 Your Free Welcome Package is Here!</h3>
                    <p>I've attached three essential recovery resources created from real recovery experience:</p>
                    <ul>
                        <li><strong>Welcome Guide</strong> - Everything you need to know about our community and getting started</li>
                        <li><strong>Daily Affirmations</strong> - 30 powerful affirmations for every stage of recovery</li>
                        <li><strong>Milestone Tracker</strong> - Celebrate your progress from day 1 to years of recovery</li>
                    </ul>
                </div>
                
                <div class="resources">
                    <h3>What Makes This Different?</h3>
                    <p><strong>Authentic Experience:</strong> Every resource is created by someone with real recovery experience - not corporate wellness programs.</p>
                    <p><strong>Peer-Led Support:</strong> We understand because we've walked this path ourselves.</p>
                    <p><strong>Community Focus:</strong> You're joining a movement of people who believe recovery is possible.</p>
                </div>
                
                <h3>What's Next?</h3>
                <ul>
                    <li>Download and read your welcome guide</li>
                    <li>Start using the daily affirmations</li>
                    <li>Set up your milestone tracker</li>
                    <li>Visit our website to download your complete 30-Day Recovery Journal</li>
                    <li>Follow us on social media for daily inspiration</li>
                </ul>
                
                <div class="highlight">
                    <h3>📖 Premium Recovery Journal Available</h3>
                    <p>Ready to take your recovery to the next level? Our comprehensive 30-Day Recovery Journal offers personalized tracking, progress analytics, and secure cloud storage for just $19.99/month.</p>
                    <a href="#" class="button">Subscribe to Premium Journal</a>
                </div>
                
                <div class="highlight">
                    <h3>🤝 Connect With Us</h3>
                    <p>Follow our social media for daily recovery inspiration:</p>
                    <ul>
                        <li>Instagram: @eyes_of_an_addict</li>
                        <li>TikTok: @eyes_of_a_addict</li>
                        <li>Website: Visit our community page anytime</li>
                    </ul>
                </div>
                
                <p><strong>Remember:</strong> Recovery is a journey, not a destination. Every day you choose recovery, you're making progress. You're not alone in this - our entire community is here to support you.</p>
                
                <p>Stay strong, stay connected, and remember - one day at a time.</p>
                
                <p>With recovery pride,<br>
                <strong>D. Bailey, CPRSS</strong><br>
                <em>Eyes of an Addict - Recovery Community</em></p>
            </div>
            
            <div class="footer">
                <p>Eyes of an Addict - Recovery Community</p>
                <p>Created by peers, for peers | 5+ years recovery experience</p>
                <p>Questions? Email us at info@eyesofanaddict.online - we read every message!</p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        {greeting}
        
        Welcome to Eyes of an Addict Recovery Community!
        
        Thank you for joining our authentic, peer-led recovery community. I'm D. Bailey, a Certified Peer Recovery Support Specialist with over 5 years in recovery.
        
        YOUR WELCOME PACKAGE:
        
        I've attached three essential FREE recovery resources:
        
        1. Welcome Guide - Everything you need to know about getting started
        2. Daily Affirmations - 30 powerful affirmations for your recovery journey  
        3. Milestone Tracker - Celebrate your progress from day 1 onwards
        
        WHAT MAKES US DIFFERENT:
        
        - Authentic Experience: Created by someone with real recovery experience
        - Peer-Led Support: We understand because we've been there
        - Community Focus: You're joining a movement of recovery warriors
        
        NEXT STEPS:
        
        - Download your resources
        - Start using the daily affirmations
        - Set up your milestone tracker
        - Follow us on social media (@eyes_of_an_addict on Instagram)
        - Check out our Premium Recovery Journal subscription for advanced tools
        
        Remember: Recovery is a journey. Every day you choose recovery, you're winning. You're not alone - we're here to support you.
        
        One day at a time,
        
        D. Bailey, CPRSS
        Eyes of an Addict - Recovery Community
        
        Questions? Email us at info@eyesofanaddict.online anytime!
        """

        # Create the email
        mail = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content
        )

        # Add attachments
        try:
            # Welcome Guide
            with open('static/downloads/welcome-guide.md', 'rb') as f:
                welcome_data = f.read()
            welcome_attachment = Attachment(
                FileContent(base64.b64encode(welcome_data).decode()),
                FileName("Eyes-of-an-Addict-Welcome-Guide.md"),
                FileType("text/markdown"),
                Disposition("attachment")
            )
            mail.add_attachment(welcome_attachment)

            # Daily Affirmations
            with open('static/downloads/daily-affirmations.md', 'rb') as f:
                affirmations_data = f.read()
            affirmations_attachment = Attachment(
                FileContent(base64.b64encode(affirmations_data).decode()),
                FileName("Daily-Recovery-Affirmations.md"),
                FileType("text/markdown"),
                Disposition("attachment")
            )
            mail.add_attachment(affirmations_attachment)

            # Milestone Tracker
            with open('static/downloads/milestone-tracker.md', 'rb') as f:
                tracker_data = f.read()
            tracker_attachment = Attachment(
                FileContent(base64.b64encode(tracker_data).decode()),
                FileName("Recovery-Milestone-Tracker.md"),
                FileType("text/markdown"),
                Disposition("attachment")
            )
            mail.add_attachment(tracker_attachment)

            # Note: 30-Day Recovery Journal is now a premium subscription service only

        except Exception as e:
            logging.error(f"Error adding attachments: {e}")
            # Continue without attachments rather than failing completely

        # Send the email
        response = sg.send(mail)
        
        if response.status_code == 202:
            logging.info(f"Welcome email sent successfully to {to_email}")
            return True
        else:
            logging.error(f"Failed to send email. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        logging.error(f"Error sending welcome email: {e}")
        return False