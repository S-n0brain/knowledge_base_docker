from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Chat(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat',
                                verbose_name='Чат пользователя')

    def __str__(self) -> str:
        return f'Чат пользователя {self.user.username}'

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages',
                             verbose_name='Чат')
    content = models.TextField(verbose_name='Содержимое сообщения')
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name='Дата и время создания')
    role = models.CharField(max_length=10, choices=[('user', 'Пользователь'), ('assistant', 'Ассистент')],
                            default='user', verbose_name='Роль')

    def __str__(self) -> str:
        return f'Сообщение {self.pk} от {self.role} в чате {self.chat.pk} | {self.content}'
    
    class Meta:
        ordering = ["created_at"]