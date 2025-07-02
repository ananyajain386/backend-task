from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
from datetime import timedelta
import json

from .models import Verification, Role


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = '/api/register_user/'
        self.login_url = '/api/login_user/'
        self.logout_url = '/api/logout_user/'
        self.verify_url = '/api/verify_email/'

        self.user_data = {
            "email": "test@example.com",
            "password": "Test@1234",
            "role": "Ops",
            "name": "Test User"
        }

    def _post_json(self, url, data):
        return self.client.post(url, data=json.dumps(data), content_type='application/json')

    def test_block_registration_without_email_verification(self):
        response = self._post_json(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("verify your email", response.json()["message"].lower())

    @patch('user_auth.views.get_connection')
    def test_request_email_verification_code(self, mock_conn):
        mock_conn.return_value = None
        response = self._post_json(self.verify_url, {"email": self.user_data["email"]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("verification code", response.json()["message"].lower())
        self.assertTrue(Verification.objects.filter(email=self.user_data["email"]).exists())

    def test_email_verification_successful(self):
        Verification.objects.create(email=self.user_data["email"], code="1234", is_expired=False)
        response = self._post_json(self.verify_url, {"email": self.user_data["email"], "code": "1234"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("verified", response.json()["message"].lower())
        self.assertTrue(Verification.objects.get(email=self.user_data["email"]).is_expired)

    def test_email_verification_invalid_code(self):
        Verification.objects.create(email=self.user_data["email"], code="9999", is_expired=False)
        response = self._post_json(self.verify_url, {"email": self.user_data["email"], "code": "1234"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("not correct", response.json()["message"].lower())

    def test_successful_registration_after_verification(self):
        Verification.objects.create(email=self.user_data["email"], code="1234", is_expired=True, is_verified=True)
        response = self._post_json(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email=self.user_data["email"]).exists())

    def test_invalid_role_rejected(self):
        data = {**self.user_data, "role": "Hacker"}
        response = self._post_json(self.register_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid role", response.json()["message"].lower())

    def test_weak_password_rejected(self):
        Verification.objects.create(email=self.user_data["email"], is_expired=True, is_verified=True)
        weak_data = {**self.user_data, "password": "weak"}
        response = self._post_json(self.register_url, weak_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid password", response.json()["message"].lower())

    def test_duplicate_email_registration(self):
        User.objects.create_user(username="existing@example.com", email="existing@example.com", password="Test@1234")
        data = {**self.user_data, "email": "existing@example.com"}
        response = self._post_json(self.register_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("email already exists", response.json()["message"].lower())

    def test_login_successful(self):
        User.objects.create_user(username=self.user_data["email"], email=self.user_data["email"], password=self.user_data["password"])
        response = self._post_json(self.login_url, {"email": self.user_data["email"], "password": self.user_data["password"]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("login successful", response.json()["message"].lower())

    def test_login_invalid_password(self):
        User.objects.create_user(username=self.user_data["email"], email=self.user_data["email"], password=self.user_data["password"])
        response = self._post_json(self.login_url, {"email": self.user_data["email"], "password": "Wrong123"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("incorrect credentials", response.json()["message"].lower())

    def test_logout_successful(self):
        user = User.objects.create_user(username=self.user_data["email"], email=self.user_data["email"], password=self.user_data["password"])
        self.client.force_login(user)
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("logout successful", response.json()["message"].lower())

    def test_logout_without_login(self):
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("not authenticated", response.json()["message"].lower())

    def test_verification_code_expired(self):
        expired_time = timezone.now() - timedelta(minutes=3)
        Verification.objects.create(
            email=self.user_data["email"],
            code="1234",
            is_expired=False,
            created_at=expired_time
        )
        with patch('user_auth.views.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = timezone.now()
            response = self._post_json(self.verify_url, {"email": self.user_data["email"], "code": "1234"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("expired code", response.json()["message"].lower())

    def test_verification_fails_if_code_does_not_exist(self):
        response = self._post_json(self.verify_url, {"email": self.user_data["email"], "code": "1234"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("does not exist", response.json()["message"].lower())
