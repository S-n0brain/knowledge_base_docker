from django.contrib import admin
from .models import Chat, Message, UserDailyTokens

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'role', 'is_rag', 'view_message', 'created_at']
    list_display_links = ['id', 'chat']
    list_per_page = 50

    @admin.display(description='Сообщение')
    def view_message(self, obj:Message):
        return f'{obj._content[:15]}...' if obj._content else b""

admin.site.register(Chat)
admin.site.register(UserDailyTokens)