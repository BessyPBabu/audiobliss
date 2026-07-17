import io
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from user_log.models import Account, OTP, Wallet, WalletHistory
from user_log.forms import AccountUpdateForm
import services.user_service as user_service
import services.wallet_service as wallet_service


def make_image_file(name='avatar.png', size=(20, 20), content_type='image/png'):
    buf = io.BytesIO()
    Image.new('RGB', size, color='blue').save(buf, format='PNG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type=content_type)


def create_account(email='user@example.com', username='testuser', password='StrongPass123!', is_admin=False):
    user = Account.objects.create_user(email=email, username=username, password=password)
    if is_admin:
        user.is_admin = True
        user.save(update_fields=['is_admin'])
    return user


class OTPModelTests(TestCase):
    def setUp(self):
        self.user = create_account()

    def test_otp_auto_generated_on_save(self):
        otp = OTP.objects.create(user=self.user)
        self.assertEqual(len(otp.otp), 6)
        self.assertTrue(otp.otp.isdigit())

    def test_register_failed_attempt_locks_after_max(self):
        otp = OTP.objects.create(user=self.user)
        for _ in range(OTP.MAX_ATTEMPTS - 1):
            otp.register_failed_attempt()
            self.assertFalse(otp.is_locked())
        otp.register_failed_attempt()
        self.assertTrue(otp.is_locked())
        self.assertFalse(otp.is_active)


class WalletServiceTests(TestCase):
    def setUp(self):
        self.user = create_account()

    def test_credit_increases_balance_and_logs_history(self):
        wallet_service.credit(self.user, 100)
        wallet = wallet_service.get_or_create_wallet(self.user)
        self.assertEqual(wallet.balance, 100)
        self.assertEqual(WalletHistory.objects.filter(wallet=wallet).count(), 1)

    def test_credit_rejects_non_positive_amount(self):
        with self.assertRaises(ValueError):
            wallet_service.credit(self.user, 0)
        with self.assertRaises(ValueError):
            wallet_service.credit(self.user, -50)

    def test_debit_decreases_balance(self):
        wallet_service.credit(self.user, 200)
        wallet_service.debit(self.user, 75)
        self.assertEqual(wallet_service.get_balance(self.user), 125)

    def test_debit_insufficient_balance_raises(self):
        wallet_service.credit(self.user, 10)
        with self.assertRaises(ValueError):
            wallet_service.debit(self.user, 50)
        # balance must be unchanged after a failed debit
        self.assertEqual(wallet_service.get_balance(self.user), 10)

    def test_can_pay_with_wallet(self):
        wallet_service.credit(self.user, 100)
        self.assertTrue(wallet_service.can_pay_with_wallet(self.user, 100))
        self.assertFalse(wallet_service.can_pay_with_wallet(self.user, 101))


class UserServiceOTPTests(TestCase):
    def setUp(self):
        self.user = create_account()

    @mock.patch('services.user_service.send_mail')
    def test_create_and_send_otp_deactivates_old_otps(self, mock_send):
        first = user_service.create_and_send_otp(self.user)
        second = user_service.create_and_send_otp(self.user)
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertEqual(mock_send.call_count, 2)

    def test_verify_otp_success(self):
        otp = OTP.objects.create(user=self.user, otp='123456')
        success, msg = user_service.verify_otp(self.user, '123456')
        self.assertTrue(success)
        otp.refresh_from_db()
        self.assertFalse(otp.is_active)

    def test_verify_otp_wrong_code_increments_attempts(self):
        OTP.objects.create(user=self.user, otp='123456')
        success, msg = user_service.verify_otp(self.user, '000000')
        self.assertFalse(success)
        self.assertIn('attempt', msg.lower())

    def test_verify_otp_locks_after_max_attempts(self):
        OTP.objects.create(user=self.user, otp='123456')
        for _ in range(OTP.MAX_ATTEMPTS):
            success, msg = user_service.verify_otp(self.user, '000000')
        self.assertFalse(success)
        self.assertIn('too many', msg.lower())

    def test_verify_otp_expired(self):
        otp = OTP.objects.create(user=self.user, otp='123456')
        otp.created_at = timezone.now() - timedelta(minutes=user_service.OTP_VALIDITY_MINUTES + 1)
        otp.save(update_fields=['created_at'])
        success, msg = user_service.verify_otp(self.user, '123456')
        self.assertFalse(success)
        self.assertIn('expired', msg.lower())

    def test_verify_otp_no_active_otp(self):
        success, msg = user_service.verify_otp(self.user, '123456')
        self.assertFalse(success)
        self.assertIn('no active otp', msg.lower())


class ResetPasswordValidatorTests(TestCase):
    def setUp(self):
        self.user = create_account(email='pwtest@example.com', username='pwtest')

    def test_reset_password_rejects_common_password(self):
        with self.assertRaises(DjangoValidationError):
            user_service.reset_user_password(self.user, 'password')

    def test_reset_password_rejects_too_short(self):
        with self.assertRaises(DjangoValidationError):
            user_service.reset_user_password(self.user, 'abc12')

    def test_reset_password_accepts_strong_password(self):
        user_service.reset_user_password(self.user, 'Xq9#mZp2Lw!7')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Xq9#mZp2Lw!7'))


class AccountUpdateFormImageValidationTests(TestCase):
    def test_valid_image_passes(self):
        form = AccountUpdateForm(data={'username': 'validuser', 'phone': ''})
        form.cleaned_data = {'profile_image': make_image_file()}
        self.assertEqual(form.clean_profile_image(), form.cleaned_data['profile_image'])

    def test_oversized_image_rejected(self):
        big_file = make_image_file()
        big_file.size = 6 * 1024 * 1024  # simulate 6MB
        form = AccountUpdateForm(data={'username': 'validuser', 'phone': ''})
        form.cleaned_data = {'profile_image': big_file}
        with self.assertRaises(Exception):
            form.clean_profile_image()

    def test_wrong_content_type_rejected(self):
        bad_file = SimpleUploadedFile('shell.php', b'<?php echo "x"; ?>', content_type='application/x-php')
        form = AccountUpdateForm(data={'username': 'validuser', 'phone': ''})
        form.cleaned_data = {'profile_image': bad_file}
        with self.assertRaises(Exception):
            form.clean_profile_image()

    def test_non_image_bytes_with_image_content_type_rejected(self):
        fake_image = SimpleUploadedFile('fake.png', b'not-actually-an-image', content_type='image/png')
        form = AccountUpdateForm(data={'username': 'validuser', 'phone': ''})
        form.cleaned_data = {'profile_image': fake_image}
        with self.assertRaises(Exception):
            form.clean_profile_image()


class LoginThrottleViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = create_account(email='throttle@example.com', username='throttleuser', password='CorrectPass123!')

    def test_lockout_after_repeated_failed_logins(self):
        url = reverse('userlog:user_login')
        for _ in range(5):
            self.client.post(url, {'email': self.user.email, 'password': 'WrongPass'})

        # 6th attempt, even with the correct password, must be locked out
        response = self.client.post(url, {'email': self.user.email, 'password': 'CorrectPass123!'}, follow=True)
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('too many' in m.lower() for m in messages))

    def test_successful_login_clears_throttle_counter(self):
        url = reverse('userlog:user_login')
        self.client.post(url, {'email': self.user.email, 'password': 'WrongPass'})
        response = self.client.post(url, {'email': self.user.email, 'password': 'CorrectPass123!'})
        self.assertEqual(response.status_code, 302)  # redirected on success