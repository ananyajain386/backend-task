from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from auth_app.models import UserRole
from .models import File
from share.views import fernet

class SecureFileShareTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.upload_url = '/api/upload_file/'
        self.list_url = '/api/list_files/'
        self.download_url = '/api/download-file/'

        self.ops_user = User.objects.create_user('ops@example.com', 'ops@example.com', 'Test@1234')
        self.client_user = User.objects.create_user('client@example.com', 'client@example.com', 'Test@1234')
        UserRole.objects.create(user=self.ops_user, role='Ops')
        UserRole.objects.create(user=self.client_user, role='Client')

        self.file_data = b"Test content"
        self.valid_file = SimpleUploadedFile("sample.docx", self.file_data, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def upload_file(self, user, file=None):
        self.client.force_login(user)
        return self.client.post(self.upload_url, {'file': file or self.valid_file}, format='multipart')

    def test_ops_upload_and_client_restrictions(self):
        self.assertEqual(self.upload_file(self.ops_user).status_code, 200)
        self.assertEqual(self.upload_file(self.client_user).status_code, 403)
        self.assertEqual(self.client.post(self.upload_url, {'file': self.valid_file}).status_code, 302)

    def test_invalid_uploads(self):
        self.client.force_login(self.ops_user)
        invalid = SimpleUploadedFile("file.txt", b"txt", content_type="text/plain")
        self.assertEqual(self.client.post(self.upload_url, {'file': invalid}, format='multipart').status_code, 400)
        self.assertEqual(self.client.post(self.upload_url, {}, format='multipart').status_code, 400)

    def test_client_file_listing(self):
        self.client.force_login(self.client_user)
        File.objects.create(owner=self.ops_user, file_name=self.valid_file, file_size_kb=1)
        self.assertEqual(len(self.client.get(self.list_url).json().get('files')), 1)

    def test_role_based_file_listing(self):
        self.client.force_login(self.ops_user)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_file_download_link_and_token_validation(self):
        self.client.force_login(self.client_user)
        file = File.objects.create(owner=self.ops_user, file_name=self.valid_file, file_size_kb=1)
        token = fernet.encrypt(f"{self.client_user.id}:{file.id}".encode()).decode()
        resp = self.client.get(f"{self.download_url}{file.id}/")
        self.assertIn("download-link", resp.json())
        self.assertEqual(self.client.get(f"/api/secure-download/{token}/").status_code, 200)

    def test_invalid_secure_downloads(self):
        self.client.force_login(self.client_user)
        file = File.objects.create(owner=self.ops_user, file_name=self.valid_file, file_size_kb=1)
        token = fernet.encrypt(f"{self.ops_user.id}:{file.id}".encode()).decode()
        self.assertEqual(self.client.get(f"/api/secure-download/{token}/").status_code, 403)
        self.assertEqual(self.client.get("/api/secure-download/invalid/" ).status_code, 400)

    def test_soft_delete_hides_files(self):
        self.client.force_login(self.client_user)
        File.objects.create(owner=self.ops_user, file_name=self.valid_file, file_size_kb=1, status=False)
        self.assertEqual(len(self.client.get(self.list_url).json().get("files")), 0)

    def test_last_opened_updates_on_download(self):
        self.client.force_login(self.client_user)
        file = File.objects.create(owner=self.ops_user, file_name=self.valid_file, file_size_kb=1)
        token = fernet.encrypt(f"{self.client_user.id}:{file.id}".encode()).decode()
        old_time = file.last_opened
        self.client.get(f"/api/secure-download/{token}/")
        file.refresh_from_db()
        self.assertNotEqual(file.last_opened, old_time)
