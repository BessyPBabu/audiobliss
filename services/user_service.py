import logging
import random
import string
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

OTP_VALIDITY_MINUTES = 5


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp_code):
    subject = 'OTP Verification - Audio Bliss'
    message = f'Your OTP is {otp_code}. It is valid for {OTP_VALIDITY_MINUTES} minutes.'
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
        logger.info("OTP email sent to %s", email)
    except Exception:
        logger.exception("Failed to send OTP email to %s", email)
        raise


def create_and_send_otp(user):
    from apps.users.models import OTP
    # Deactivate existing OTPs
    OTP.objects.filter(user=user, is_active=True).update(is_active=False)
    otp = OTP.objects.create(user=user)
    send_otp_email(user.email, otp.otp)
    return otp


def verify_otp(user, otp_code):
    from apps.users.models import OTP
    otp = OTP.objects.filter(user=user, is_active=True).order_by('-created_at').first()

    if otp is None:
        return False, "No active OTP found."

    if (timezone.now() - otp.created_at) > timedelta(minutes=OTP_VALIDITY_MINUTES):
        otp.is_active = False
        otp.save(update_fields=['is_active'])
        return False, "OTP has expired."

    if otp.otp != otp_code:
        return False, "Invalid OTP."

    otp.is_active = False
    otp.save(update_fields=['is_active'])
    logger.info("OTP verified for user %s", user.id)
    return True, "OTP verified successfully."


def can_resend_otp(user):
    from apps.users.models import OTP
    recent = OTP.objects.filter(user=user, is_active=True).order_by('-created_at').first()
    if recent and (timezone.now() - recent.created_at) < timedelta(minutes=OTP_VALIDITY_MINUTES):
        return False
    return True


def activate_user(user):
    user.is_active = True
    user.save(update_fields=['is_active'])
    logger.info("Activated user %s", user.id)


def reset_user_password(user, new_password):
    user.set_password(new_password)
    user.save(update_fields=['password'])
    logger.info("Password reset for user %s", user.id)


def initiate_email_update(user, new_email):
    from apps.users.models import Account
    if Account.objects.filter(email=new_email).exclude(pk=user.pk).exists():
        raise ValueError("This email address is already in use.")
    user.new_email = new_email
    user.is_new_email_verified = False
    user.save(update_fields=['new_email', 'is_new_email_verified'])
    send_otp_email(new_email, create_and_send_otp(user).otp)


def confirm_email_update(user):
    if not user.new_email:
        raise ValueError("No pending email update found.")
    user.email = user.new_email
    user.new_email = None
    user.is_new_email_verified = False
    user.save(update_fields=['email', 'new_email', 'is_new_email_verified'])
    logger.info("Email updated for user %s", user.id)
