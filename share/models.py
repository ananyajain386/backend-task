from django.db import models
from django.contrib.auth.models import User
from auth.models import BaseModel

class File(BaseModel):
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='user_files/', null=True, blank=True)
    file_size_kb = models.BigIntegerField(null=True, help_text="Size in KB")
    last_opened = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.file.name if self.file else "Unnamed File"
