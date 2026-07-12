"""Email content - all text and HTML content for emails.

This file contains ONLY the actual email content that non-technical people
can safely edit. No code, no logic, just content.
"""

# ============================================================
# AUTHENTICATION EMAILS
# ============================================================

# Welcome Email
WELCOME_SUBJECT = "Welcome to Voya! 🎉"
WELCOME_TITLE = "Welcome to Voya"
WELCOME_CONTENT = """
<h2 style="color: #28a745;">Welcome aboard! 🎉</h2>
<p>We're thrilled to have you join the Voya community. Here's what you can do now:</p>
<ul>
    <li>Search and book flights to amazing destinations</li>
    <li>Manage your bookings in one place</li>
    <li>Get exclusive deals and offers</li>
    <li>24/7 customer support</li>
</ul>
<p>Ready to start your journey? Click below to explore!</p>
"""
WELCOME_BUTTON_TEXT = "Start Exploring"

# Email Verified
EMAIL_VERIFIED_SUBJECT = "Email verified successfully ✅"
EMAIL_VERIFIED_TITLE = "Email Verified"
EMAIL_VERIFIED_CONTENT = """
<div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0;">
    ✅ Your email has been successfully verified!
</div>
<p>Your account is now fully activated and you have access to all features.</p>
<p>You can now enjoy the full Voya experience!</p>
"""
EMAIL_VERIFIED_BUTTON_TEXT = "Go to Your Profile"

# Password Reset
PASSWORD_RESET_SUBJECT = "Reset your Voya password"  # noqa: S105 # nosec B105 - Email subject
PASSWORD_RESET_TITLE = "Password Reset Request"  # noqa: S105 # nosec B105 - Email title
PASSWORD_RESET_CONTENT = (  # nosec B105
    """<p>We received a request to reset your password. Click the button below to create a new password:</p>
<p><strong>⏰ This link will expire in 1 hour for security reasons.</strong></p>
<p style="color: #6c757d;">If you didn't request a password reset, please ignore this email. Your password won't be changed.</p>
"""
)
PASSWORD_RESET_BUTTON_TEXT = "Reset Password"  # noqa: S105 # nosec B105 - Button text

# PII Verification OTP
PII_VERIFICATION_OTP_SUBJECT = "Your Voya verification code"
PII_VERIFICATION_OTP_TITLE = "Verify Your Identity"
PII_VERIFICATION_OTP_CONTENT = """
<p>Use this code to view your passport information in Voya:</p>
<p style="font-size: 24px; font-weight: bold; letter-spacing: 4px; font-family: monospace;">{otp}</p>
<p style="color: #6c757d; font-size: 0.9em;">This code expires in 10 minutes. If you didn't request this, you can safely ignore this email.</p>
"""
PII_VERIFICATION_OTP_BUTTON_TEXT = "Go to Profile"

# Password Changed
PASSWORD_CHANGED_SUBJECT = "Your Voya password has been changed"  # noqa: S105 # nosec B105 - Email subject
PASSWORD_CHANGED_TITLE = "Password Changed"  # noqa: S105 # nosec B105 - Email title
PASSWORD_CHANGED_CONTENT = (  # nosec B105
    """<div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0;">
    Your password has been successfully changed.
</div>
<p>If you made this change, you can safely ignore this email.</p>
<p><strong>Didn't change your password?</strong> Your account may be compromised. Please contact our support team immediately.</p>
"""
)
PASSWORD_CHANGED_BUTTON_TEXT = "Contact Support"  # noqa: S105 # nosec B105 - Button text

# Registration Setup
REGISTRATION_SETUP_SUBJECT = "Complete your Voya registration"
REGISTRATION_SETUP_TITLE = "Complete Your Registration"
REGISTRATION_SETUP_CONTENT = """
<p>Welcome to Voya! You're almost there - just one more step to complete your registration.</p>
<p>Click the button below to set up your password and activate your account:</p>
<p><strong>⏰ This link will expire in {expiry_hours} hours.</strong></p>
<p style="color: #6c757d;">If you didn't create an account with Voya, please ignore this email.</p>
"""
REGISTRATION_SETUP_BUTTON_TEXT = "Set Your Password"

# ============================================================
# ACCOUNT STATUS EMAILS
# ============================================================

# Account Deleted
ACCOUNT_DELETED_SUBJECT = "Your Voya account has been deleted"
ACCOUNT_DELETED_TITLE = "Account Deleted"
ACCOUNT_DELETED_CONTENT = """
<p>Your Voya account has been successfully deleted as requested.</p>
<p>We're sorry to see you go. All your personal data has been removed from our systems.</p>
<p style="color: #6c757d;">If you ever want to come back, we'll be here waiting for you!</p>
"""
ACCOUNT_DELETED_BUTTON_TEXT = "Visit Voya"

# Account Suspended
ACCOUNT_SUSPENDED_SUBJECT = "Important: Your Voya account has been suspended"
ACCOUNT_SUSPENDED_TITLE = "Account Suspended"
ACCOUNT_SUSPENDED_CONTENT = """
<div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 15px 0;">
    Your account has been temporarily suspended.
</div>
<p>During this time, you won't be able to access your account or make new bookings.</p>
{reason_block}
<p>If you believe this is a mistake, please contact our support team.</p>
"""
ACCOUNT_SUSPENDED_BUTTON_TEXT = "Contact Support"

# Account Banned
ACCOUNT_BANNED_SUBJECT = "Important: Your Voya account has been banned"
ACCOUNT_BANNED_TITLE = "Account Banned"
ACCOUNT_BANNED_CONTENT = """
<div style="background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 15px 0;">
    Your account has been permanently banned.
</div>
<p>This action is permanent and your account cannot be recovered.</p>
{reason_block}
<p>If you believe this is a mistake, you may appeal by contacting support.</p>
"""
ACCOUNT_BANNED_BUTTON_TEXT = "Contact Support"

# Account Reactivated
ACCOUNT_REACTIVATED_SUBJECT = "Good news! Your Voya account has been reactivated 🎉"
ACCOUNT_REACTIVATED_TITLE = "Account Reactivated"
ACCOUNT_REACTIVATED_CONTENT = """
<div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0;">
    Great news! Your account has been reactivated.
</div>
<p>You now have full access to your Voya account and can resume using all our services.</p>
<p>Welcome back! We're glad to have you with us again.</p>
"""
ACCOUNT_REACTIVATED_BUTTON_TEXT = "Start Booking"

# ============================================================
# BOOKING EMAILS
# ============================================================

# Booking Confirmation (LCC - tickets issued)
BOOKING_CONFIRMATION_LCC_SUBJECT_TEMPLATE = (
    "✈️ Your flight tickets are confirmed - {voya_booking_reference}"
)
BOOKING_CONFIRMATION_LCC_TITLE = "Flight Booking Confirmation"
BOOKING_CONFIRMATION_LCC_CONTENT = """
<div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0;">
    🎉 Your flight tickets have been confirmed and issued!
</div>
<h3>Booking Details:</h3>
<table style="width: 100%; border-collapse: collapse;">
    <tr><td style="padding: 5px; font-weight: bold;">Booking Reference:</td><td style="padding: 5px;"><strong>{voya_booking_reference}</strong></td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Total Fare:</td><td style="padding: 5px;">{total_fare}</td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Status:</td><td style="padding: 5px;"><span style="color: #28a745;">✅ Tickets Issued</span></td></tr>
</table>
<p style="margin-top: 20px;"><strong>What's next?</strong></p>
<ul>
    <li>Check-in online 24-48 hours before departure</li>
    <li>Arrive at the airport at least 2 hours before your flight</li>
    <li>Have your passport/ID and booking reference ready</li>
</ul>
{cancellation_policy_section}
"""
BOOKING_CONFIRMATION_LCC_BUTTON_TEXT = (
    "View Your Booking"  # Button to view booking details
)

# Booking Confirmation (FSC - payment required)
BOOKING_CONFIRMATION_FSC_SUBJECT_TEMPLATE = (
    "📋 Booking confirmed - Action required - {voya_booking_reference}"
)
BOOKING_CONFIRMATION_FSC_TITLE = "Flight Booking Confirmation"
BOOKING_CONFIRMATION_FSC_CONTENT = """
<div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 15px 0;">
    📋 Your booking is confirmed - Action Required!
</div>
<h3>Booking Details:</h3>
<table style="width: 100%; border-collapse: collapse;">
    <tr><td style="padding: 5px; font-weight: bold;">Booking Reference:</td><td style="padding: 5px;"><strong>{voya_booking_reference}</strong></td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Total Fare:</td><td style="padding: 5px;">{total_fare}</td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Payment Deadline:</td><td style="padding: 5px;"><strong style="color: #721c24;">{ticket_time_limit}</strong></td></tr>
</table>
<div style="background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 15px 0;">
    <strong>⚠️ Important:</strong> You must complete payment before the deadline or your booking will be automatically cancelled.
</div>
<p>Once payment is received, your tickets will be issued immediately.</p>
"""
BOOKING_CONFIRMATION_FSC_BUTTON_TEXT = "Proceed to Checkout"

# Hotel Booking Confirmation
HOTEL_BOOKING_CONFIRMATION_SUBJECT_TEMPLATE = (
    "🏨 Your hotel reservation is confirmed - {voya_booking_reference}"
)
HOTEL_BOOKING_CONFIRMATION_TITLE = "Hotel Booking Confirmation"
HOTEL_BOOKING_CONFIRMATION_CONTENT = """
<div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0;">
    🎉 Your hotel reservation has been confirmed!
</div>
<h3>Booking Details:</h3>
<table style="width: 100%; border-collapse: collapse;">
    <tr><td style="padding: 5px; font-weight: bold;">VOYA Reference:</td><td style="padding: 5px;"><strong>{voya_booking_reference}</strong></td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Hotel Confirmation:</td><td style="padding: 5px;"><strong>{supplier_confirmation_num}</strong></td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Hotel Name:</td><td style="padding: 5px;">{hotel_name}</td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Check-in:</td><td style="padding: 5px;">{check_in_date}</td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Check-out:</td><td style="padding: 5px;">{check_out_date}</td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Total Price:</td><td style="padding: 5px;"><strong>{total_price}</strong></td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Status:</td><td style="padding: 5px;"><span style="color: #28a745;">✅ Confirmed</span></td></tr>
</table>
<p style="margin-top: 20px;"><strong>What's next?</strong></p>
<ul>
    <li>Check-in time is typically 15:00 (3:00 PM)</li>
    <li>Check-out time is typically 11:00 AM</li>
    <li>Bring a valid ID and this confirmation number</li>
    <li>Contact the hotel directly if you have special requests</li>
</ul>
<p style="color: #6c757d; font-size: 0.9em; margin-top: 20px;">
    <strong>Need to make changes?</strong> Contact us at support@myvoya.ai with your booking reference.
</p>
"""
HOTEL_BOOKING_CONFIRMATION_BUTTON_TEXT = "View Booking Details"

# Ticket Confirmation
TICKET_CONFIRMATION_SUBJECT_TEMPLATE = (
    "✈️ Your flight tickets are ready - {voya_booking_reference}"
)
TICKET_CONFIRMATION_TITLE = "Flight Tickets Issued"
TICKET_CONFIRMATION_CONTENT = """
<div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0;">
    ✈️ Your flight tickets have been issued!
</div>
<p><strong>Booking Reference:</strong> {voya_booking_reference}</p>
<p><strong>Ticket Numbers:</strong> {ticket_numbers}</p>
<p>Your ticket is attached. Keep your tickets safe - you'll need them for check-in and boarding. Happy voyage! 🌍</p>
{cancellation_policy_section}
"""
TICKET_CONFIRMATION_BUTTON_TEXT = "View Your Tickets"

# Booking Failed
BOOKING_FAILED_SUBJECT = "Your flight booking could not be completed - Refund initiated"
BOOKING_FAILED_TITLE = "Booking Failed - Refund Initiated"
BOOKING_FAILED_CONTENT = """
<div style="background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 15px 0;">
    Unfortunately, your booking could not be completed.
</div>
<p><strong>Reason:</strong> {reason}</p>
<h3>Refund Information:</h3>
<div style="background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 15px 0;">
    <p><strong>Refund Reference:</strong> {refund_reference}</p>
    <p><strong>Processing Time:</strong> {estimated_refund_days} business days</p>
    <p>The refund will be credited to your original payment method.</p>
</div>
<p>We apologize for the inconvenience. Please try booking again or contact support if you need assistance.</p>
"""
BOOKING_FAILED_BUTTON_TEXT = "Search for Alternative Flights"

# Payment Confirmation
PAYMENT_CONFIRMATION_SUBJECT_TEMPLATE = "💳 Payment received - {voya_booking_reference}"
PAYMENT_CONFIRMATION_TITLE = "Payment Confirmed"
PAYMENT_CONFIRMATION_CONTENT = """
<div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0;">
    💳 Your payment has been successfully processed!
</div>
<h3>Payment Details:</h3>
<table style="width: 100%; border-collapse: collapse;">
    <tr><td style="padding: 5px; font-weight: bold;">Booking Reference:</td><td style="padding: 5px;"><strong>{voya_booking_reference}</strong></td></tr>
    {hotel_name_row}
    <tr><td style="padding: 5px; font-weight: bold;">Amount Paid:</td><td style="padding: 5px;"><strong>{amount_paid}</strong></td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Payment Method:</td><td style="padding: 5px;">{payment_method}</td></tr>
    <tr><td style="padding: 5px; font-weight: bold;">Transaction ID:</td><td style="padding: 5px; font-family: monospace; font-size: 0.9em;">{transaction_id}</td></tr>
</table>
<div style="background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 15px 0;">
    <strong>What's next?</strong>
    <p>Your flight tickets will be issued shortly. You'll receive a separate email with your e-tickets and booking details once processing is complete.</p>
</div>
<p style="color: #6c757d; font-size: 0.9em;">Keep this email for your records. You can view your booking details anytime using your booking reference.</p>
"""
PAYMENT_CONFIRMATION_BUTTON_TEXT = "View Your Booking"

# Booking Cancelled
BOOKING_CANCELLED_SUBJECT_TEMPLATE = "Booking cancelled - {voya_booking_reference}"
BOOKING_CANCELLED_TITLE = "Booking Cancelled"
BOOKING_CANCELLED_CONTENT = """
<div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 15px 0;">
    Your booking has been cancelled.
</div>
<p><strong>Booking Reference:</strong> {voya_booking_reference}</p>
<p>If you have any questions about this cancellation or need to make a new booking, our support team is here to help.</p>
"""
BOOKING_CANCELLED_BUTTON_TEXT = "Contact Support"
