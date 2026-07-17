from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse

from admin_log.backends import CustomAdminBackend
from admin_log.decorators import admin_required
from user_log.models import Account
import services.security_service as security_service


def create_account(email, username, password='Pass1234!', is_admin=False):
    user = Account.objects.create_user(email=email, username=username, password=password)
    user.is_admin = is_admin
    user.save(update_fields=['is_admin'])
    return user


class SecurityServiceThrottleTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_not_locked_out_initially(self):
        self.assertFalse(security_service.is_locked_out('test', 'someone@example.com'))

    def test_locks_out_after_max_attempts(self):
        for _ in range(security_service.MAX_ATTEMPTS):
            security_service.register_failed_attempt('test', 'someone@example.com')
        self.assertTrue(security_service.is_locked_out('test', 'someone@example.com'))

    def test_clear_attempts_resets_lockout(self):
        for _ in range(security_service.MAX_ATTEMPTS):
            security_service.register_failed_attempt('test', 'someone@example.com')
        security_service.clear_attempts('test', 'someone@example.com')
        self.assertFalse(security_service.is_locked_out('test', 'someone@example.com'))

    def test_lockout_keys_are_isolated_per_prefix(self):
        for _ in range(security_service.MAX_ATTEMPTS):
            security_service.register_failed_attempt('login', 'x@example.com')
        self.assertFalse(security_service.is_locked_out('otp', 'x@example.com'))


class AdminRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = create_account('admin@example.com', 'adminuser', is_admin=True)
        self.regular_user = create_account('regular@example.com', 'regularuser', is_admin=False)

        @admin_required
        def dummy_view(request):
            from django.http import HttpResponse
            return HttpResponse('ok')

        self.dummy_view = dummy_view

    def _attach_messages(self, request):

        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        SessionMiddleware(lambda r: None).process_request(request)
        request.session.save()
        MessageMiddleware(lambda r: None).process_request(request)
        return request

    def test_anonymous_user_redirected(self):
        request = self.factory.get('/admin-only/')
        request.user = AnonymousUser()
        request = self._attach_messages(request)
        response = self.dummy_view(request)
        self.assertEqual(response.status_code, 302)

    def test_non_admin_authenticated_user_redirected(self):
        request = self.factory.get('/admin-only/')
        request.user = self.regular_user
        request = self._attach_messages(request)
        response = self.dummy_view(request)
        self.assertEqual(response.status_code, 302)

    def test_admin_user_allowed_through(self):
        request = self.factory.get('/admin-only/')
        request.user = self.admin_user
        request = self._attach_messages(request)
        response = self.dummy_view(request)
        self.assertEqual(response.status_code, 200)


class CustomAdminBackendTests(TestCase):
    def setUp(self):
        self.backend = CustomAdminBackend()
        self.admin_user = create_account('admin2@example.com', 'admin2', password='AdminPass1!', is_admin=True)
        self.non_admin_user = create_account('plain@example.com', 'plainuser', password='PlainPass1!', is_admin=False)

    def test_missing_credentials_returns_none(self):
        self.assertIsNone(self.backend.authenticate(None, email=None, password=None))

    def test_nonexistent_email_returns_none_without_raising(self):
        result = self.backend.authenticate(None, email='ghost@example.com', password='whatever')
        self.assertIsNone(result)

    def test_non_admin_user_cannot_authenticate_via_admin_backend(self):
        result = self.backend.authenticate(None, email='plain@example.com', password='PlainPass1!')
        self.assertIsNone(result)

    def test_wrong_password_returns_none(self):
        result = self.backend.authenticate(None, email='admin2@example.com', password='WrongPass')
        self.assertIsNone(result)

    def test_correct_admin_credentials_return_user(self):
        result = self.backend.authenticate(None, email='admin2@example.com', password='AdminPass1!')
        self.assertEqual(result, self.admin_user)


class AdminLoginViewThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin_user = create_account('adminlogin@example.com', 'adminloginuser', password='AdminPass1!', is_admin=True)

    def test_lockout_after_repeated_failed_admin_logins(self):
        url = reverse('adminlog:admin_login')
        for _ in range(5):
            self.client.post(url, {'email': self.admin_user.email, 'password': 'WrongPass'})

        response = self.client.post(
            url, {'email': self.admin_user.email, 'password': 'AdminPass1!'}, follow=True
        )
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('too many' in m.lower() for m in messages))

    def test_non_admin_cannot_reach_dashboard(self):
        non_admin = create_account('notadmin@example.com', 'notadminuser', password='Pass1234!', is_admin=False)
        self.client.login(email='notadmin@example.com', password='Pass1234!')
        response = self.client.get(reverse('adminlog:admin_dashboard'))
        self.assertEqual(response.status_code, 302)