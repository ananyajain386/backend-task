from django.db import models
from django.contrib.auth.models import User

class DeletedManager(models.Manager):
    def get_queryset(self):
        return super(DeletedManager, self).get_queryset().exclude(status=False)
    
class BaseModel(models.Model):
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    objects = DeletedManager()

    class Meta:
        abstract = True

class UserRole(BaseModel):
    OPS = 'Ops'
    CLIENT = 'Client'
    ROLE_CHOICES = [
        (OPS, 'Ops'),
        (CLIENT, 'Client'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='user_detail')
    
class EmailVerification(BaseModel):
    code = models.IntegerField(null=True)
    is_verified = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    email = models.CharField(max_length=100)
