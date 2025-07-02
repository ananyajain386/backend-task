import os
import json
import datetime
from cryptography.fernet import Fernet
from django.http import JsonResponse, FileResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.conf import settings
from auth.models import Role
from .models import File

# Constants
ALLOWED_EXTENSIONS = ['.pptx', '.docx', '.xlsx']
OPS_ROLE = 'Ops'
CLIENT_ROLE = 'Client'

# Securely load FERNET key
FERNET_KEY = os.environ.get('FERNET_KEY')
if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY environment variable not set.")
fernet = Fernet(FERNET_KEY)

# Utils
def get_user_role(user):
    role_obj = Role.objects.filter(user=user).last()
    return role_obj.role if role_obj else None

def is_valid_file(file):
    ext = os.path.splitext(file.name)[1].lower()
    return ext in ALLOWED_EXTENSIONS

# Views
@login_required
def upload_file(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method.'}, status=405)

    user = request.user
    if get_user_role(user) != OPS_ROLE:
        return HttpResponseForbidden("Only Ops users can upload files.")

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'message': 'No file provided.'}, status=400)

    if not is_valid_file(file):
        return JsonResponse({'message': 'Invalid file type.'}, status=400)

    saved_file = File.objects.create(
        owner=user,
        file_name=file,
        file_size_kb=file.size // 1024
    )

    return JsonResponse({
        'message': 'File uploaded successfully.',
        'file_id': saved_file.id
    }, status=201)

@login_required
def list_files(request):
    user = request.user
    if get_user_role(user) != CLIENT_ROLE:
        return HttpResponseForbidden("Only Client users can list files.")

    files = File.objects.filter(status=True).order_by('-last_opened')
    file_list = [
        {
            'id': f.id,
            'file_name': os.path.basename(f.file_name.name),
            'file_size_kb': f.file_size_kb,
            'last_opened': f.last_opened
        }
        for f in files
    ]
    return JsonResponse({'files': file_list}, status=200)

@login_required
def download_file(request, file_id):
    user = request.user
    if get_user_role(user) != CLIENT_ROLE:
        return HttpResponseForbidden("Only Client users can download files.")

    try:
        file_obj = File.objects.get(id=file_id, status=True)
    except File.DoesNotExist:
        return JsonResponse({'message': 'File not found.'}, status=404)

    token_data = f"{user.id}:{file_obj.id}".encode()
    token = fernet.encrypt(token_data).decode()

    download_link = request.build_absolute_uri(
        reverse('secure_download', args=[token])
    )

    return JsonResponse({
        'message': 'Download link generated successfully.',
        'download_link': download_link
    }, status=200)

@login_required
def secure_download(request, token):
    try:
        decrypted = fernet.decrypt(token.encode()).decode()
        user_id, file_id = map(int, decrypted.split(':'))

        if user_id != request.user.id:
            return HttpResponseForbidden("This link is not valid for this user.")

        file_obj = File.objects.get(id=file_id, status=True)

    except Exception:
        return JsonResponse({'message': 'Invalid or expired download link.'}, status=400)

    file_path = file_obj.file_name.path
    if not os.path.exists(file_path):
        return JsonResponse({'message': 'File no longer exists.'}, status=404)

    # Update last opened
    file_obj.last_opened = datetime.datetime.now()
    file_obj.save()

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
