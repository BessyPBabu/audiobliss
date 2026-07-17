import logging
from django.contrib.auth.backends import ModelBackend
from user_log.models import Account

logger = logging.getLogger(__name__)


class CustomAdminBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None

        try:
            user = Account.objects.get(email=email)
        except Account.DoesNotExist:
            Account().set_password(password)
            logger.warning("Admin auth attempt for non-existent email: %s", email)
            return None

        if user.check_password(password) and user.is_admin:
            logger.info("Admin authenticated: %s", email)
            return user

        logger.warning("Failed admin auth attempt for email: %s", email)
        return None

    def get_user(self, user_id):
        try:
            return Account.objects.get(pk=user_id)
        except Account.DoesNotExist:
            return None