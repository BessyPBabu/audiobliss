from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import AccountManager
import random
import string


class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name="email", max_length=60, unique=True)
    username = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to='static/admin/imgs', blank=True, null=True)
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
    
    def get_available_referral_offers(self):
        from offer_management.models import ReferralOffer
        return ReferralOffer.objects.filter(
            referred=self, 
            is_claimed=False, 
            offer__is_active=True,
            offer__start_date__lte=models.functions.Now(),
            offer__end_date__gte=models.functions.Now()
        )

    def apply_referral_offer(self, referrer):
        from offer_management.models import ReferralOffer
        referral_offer = ReferralOffer.objects.filter(
            referred=self, 
            referrer=referrer, 
            is_claimed=False, 
            offer__is_active=True,
            offer__start_date__lte=models.functions.Now(),
            offer__end_date__gte=models.functions.Now()
        ).first()
        
        if referral_offer:
            referral_offer.is_claimed = True
            referral_offer.save()
            # Apply the discount or reward to the new user and/or referrer
            # You might want to implement this logic based on your specific requirements
            return True
        return False

    def has_active_referral_offer(self):
        return self.get_available_referral_offers().exists()
    
    def verify_new_email(self):
        # If the new email is verified, set the new email as the current email
        if self.is_new_email_verified:
            self.email = self.new_email
            self.new_email = None
            self.is_new_email_verified = False
            self.save()

    
class OTP(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)


class Address(models.Model):
    account=models.ForeignKey(Account,on_delete=models.CASCADE)
    house_name=models.CharField(max_length=40,null=False, blank=False)
    streat_name=models.CharField(max_length=50,null=False, blank=False)
    post_office=models.CharField( max_length=20,null=False, blank=False)
    place=models.CharField(max_length=25,null=False, blank=False)
    district=models.CharField(max_length=20, null=False, blank=False)
    state=models.CharField(max_length=30,null=False,blank=False)
    country=models.CharField(max_length=35,null=True,blank=True)
    pincode=models.CharField(max_length=10,null=True, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.house_name}, {self.streat_name}, {self.place}"
    

class Wallet(models.Model):
    user = models.OneToOneField(Account, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s Wallet"

class WalletHistory(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    type = models.CharField(null=True, blank=True, max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.wallet.user.username} - {self.type} - ₹{self.amount}"