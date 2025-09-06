from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls
from . import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('knowledge_base_app.urls', namespace='knowledge_base_app')),
    path('users/', include('users.urls', namespace='users')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('chat/', include('chatbot.urls', namespace='chatbot')),

] + debug_toolbar_urls()

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)