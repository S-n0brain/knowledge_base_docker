from django.db import models
from django.contrib.auth import get_user_model
from knowledge_base.settings import cipher

user = get_user_model()

class Chat(models.Model):
    user = models.OneToOneField(user, on_delete=models.CASCADE, related_name='chat',
                                verbose_name='Чат пользователя')

    def __str__(self) -> str:
        return f'Чат пользователя {self.user.username}'
    
    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты" 


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages',
                             verbose_name='Чат')
    _content = models.BinaryField(verbose_name='Содержимое сообщения')
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name='Дата и время создания')
    role = models.CharField(max_length=10, choices=[('user', 'Пользователь'), ('assistant', 'Ассистент')],
                            default='user', verbose_name='Роль')

    def __str__(self) -> str:
        return f'Сообщение {self.pk} от {self.role} в чате {self.chat.pk} | {self._content if self._content else ""}'

    @property
    def content(self):
        if self._content:
            try:
                return cipher.decrypt(self._content).decode()
            except Exception:
                return f"Ошибка расшифровки"
        return ""

    @content.setter
    def content(self, value):
        self._content = cipher.encrypt(value.encode())

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"


class UserDailyTokens(models.Model):
    user = models.OneToOneField(user, on_delete=models.CASCADE,
                                related_name="tokens", verbose_name="Пользователь")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    tokens_available = models.PositiveIntegerField(default=35000, verbose_name="Доступные токены")

    def __str__(self) -> str:
        return f'{self.user.username}: Токены {self.tokens_available} на {self.date}'
    
    class Meta:
        verbose_name = "Токены пользователя"
        verbose_name_plural = "Токены пользоваетелй"