from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import EmailVerification, UserRole
import json
import re
import random
import datetime
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.views.decorators.csrf import csrf_exempt

PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$'
VERIFICATION_CODE_EXPIRY_SECONDS = 120
VALID_ROLES = ['Ops', 'Client']

def is_valid_password(password):
    return re.match(PASSWORD_REGEX, password)

def send_verification_email(email, code):
    connection = get_connection(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS
    )
    subject = 'Verification Code'
    message = f'Your verification code is: {code}'
    email_msg = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [email], connection=connection)
    email_msg.send()


def register_user(request):
    if request.method != 'POST':
        return JsonResponse({"message": "Invalid request method."}, status=405)

    data = json.loads(request.body)
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    name = data.get('name')

    if not all([email, password, role, name]):
        return JsonResponse({'message': 'All fields are required.'}, status=400)

    if role not in VALID_ROLES:
        return JsonResponse({'message': 'Invalid role.'}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({'message': 'Email already exists.'}, status=400)

    verified = EmailVerification.objects.filter(email=email, is_verified=True, is_expired=True).last()
    if not verified:
        return JsonResponse({'message': 'First verify your email.'}, status=400)

    if not is_valid_password(password):
        return JsonResponse({
            'message': 'Password must contain uppercase, lowercase, digit, special character, and be 6–20 characters long.'
        }, status=400)

    user = User.objects.create_user(
        username=email,
        password=password,
        email=email,
        first_name=name
    )
    UserRole.objects.create(user=user, role=role)

    return JsonResponse({'message': 'Registration successful!'}, status=200)

def login_user(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method'}, status=405)

    data = json.loads(request.body)
    email = data.get('email')
    password = data.get('password')

    user = User.objects.filter(email=email).first()
    if not user or not user.check_password(password):
        return JsonResponse({'message': 'Incorrect credentials'}, status=403)

    auth_user = authenticate(request, username=user.username, password=password)
    if auth_user:
        login(request, auth_user)
        return JsonResponse({'message': 'Login successful'})
    return JsonResponse({'message': 'Authentication failed.'}, status=403)

def logout_user(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Invalid request method'}, status=405)

    if request.user.is_authenticated:
        logout(request)
        return JsonResponse({'message': 'Logout successful.'})
    return JsonResponse({'message': 'User is not authenticated.'}, status=401)


def verify_email(request):
    if request.method != 'POST':
        return JsonResponse({"message": "Invalid request method"}, status=405)

    data = json.loads(request.body)
    email = data.get('email')
    code = data.get('code')

    if email and not code:
        verification_code = str(random.randint(1000, 9999))
        EmailVerification.objects.create(email=email, code=verification_code)
        try:
            send_verification_email(email, verification_code)
            return JsonResponse({"message": "Verification code sent to email."}, status=200)
        except Exception as e:
            return JsonResponse({"error": f"Failed to send email: {str(e)}"}, status=500)

    elif email and code:
        record = EmailVerification.objects.filter(email=email, is_expired=False).last()
        if not record:
            return JsonResponse({"message": "Verification code not found or expired."}, status=400)

        if str(record.code) != str(code):
            return JsonResponse({"message": "Incorrect verification code."}, status=400)

        now = datetime.datetime.now(record.created_at.tzinfo)
        if (now - record.created_at).seconds > VERIFICATION_CODE_EXPIRY_SECONDS:
            record.is_expired = True
            record.save()
            return JsonResponse({"message": "Verification code expired."}, status=400)

        record.is_verified = True
        record.is_expired = True
        record.save()
        return JsonResponse({"message": "Email verified successfully."}, status=200)

    return JsonResponse({"message": "Email is required."}, status=400)
