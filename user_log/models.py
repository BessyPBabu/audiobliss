import random
import string
import logging
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import AccountManager

logger = logging.getLogger(__name__)


class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name="email", max_length=60, unique=True)
    username = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_joined = models.DateTimeField(verbose_name="date joined", auto_now_add=True)
    last_login = models.DateTimeField(verbose_name="last login", auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    new_email = models.EmailField(null=True, blank=True)
    is_new_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = AccountManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

    def toggle_active(self):
        self.is_active = not self.is_active
        self.save(update_fields=['is_active'])
        logger.info("User %s active status toggled to %s", self.id, self.is_active)

    def get_default_address(self):
        return self.addresses.filter(is_default=True).first() or self.addresses.first()

    class Meta:
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'


# new
class OTP(models.Model):
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='otps')
    otp = models.CharField(max_length=6)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)

    def register_failed_attempt(self):
        self.attempts += 1
        if self.attempts >= self.MAX_ATTEMPTS:
            self.is_active = False
            self.save(update_fields=['attempts', 'is_active'])
        else:
            self.save(update_fields=['attempts'])

    def is_locked(self):
        return self.attempts >= self.MAX_ATTEMPTS

    def __str__(self):
        return f"OTP for {self.user.email}"

    class Meta:
        ordering = ['-created_at']


class Address(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='addresses')
    house_name = models.CharField(max_length=40)
    streat_name = models.CharField(max_length=50)
    post_office = models.CharField(max_length=20)
    place = models.CharField(max_length=25)
    district = models.CharField(max_length=20)
    state = models.CharField(max_length=30)
    country = models.CharField(max_length=35, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    def set_as_default(self):
        Address.objects.filter(account=self.account).update(is_default=False)
        self.is_default = True
        self.save(update_fields=['is_default'])
        logger.info("Address %s set as default for user %s", self.id, self.account_id)

    def __str__(self):
        return f"{self.house_name}, {self.place}"

    class Meta:
        verbose_name_plural = 'Addresses'


class Wallet(models.Model):
    user = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def has_sufficient_balance(self, amount):
        from decimal import Decimal
        return self.balance >= Decimal(str(amount))

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₹{self.balance}"


class WalletHistory(models.Model):
    TRANSACTION_TYPES = (
        ('Refund', 'Refund'),
        ('Wallet Payment', 'Wallet Payment'),
    )
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='history')
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.wallet.user.username} - {self.type} - ₹{self.amount}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Wallet Histories'
