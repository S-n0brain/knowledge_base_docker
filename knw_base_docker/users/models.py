import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group

class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name='Email', blank=False)
    photo = models.ImageField(upload_to='users/%Y/%m/%d', blank=True, null=True, verbose_name='Фото')
    date_birth = models.DateTimeField(blank=True, null=True, verbose_name='Дата рождения')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class EmailConfirmation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='confirm_email')
    confirm_email = models.EmailField(blank=True, null=True)
    token = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)
    email_in_process_confirm = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} → {self.confirm_email}"

    class Meta:
        verbose_name = 'Подтверждение Email'
        verbose_name_plural = 'Подтверждения Email'