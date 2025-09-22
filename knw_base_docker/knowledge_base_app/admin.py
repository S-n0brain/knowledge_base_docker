from django import forms
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from .models import Article, ArticleChunk, Topic, Category


class ArticleFormAdmin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['published'].initial = True

    class Meta:
        model = Article
        fields = ['title', 'author', 'slug', 'topic', 'published', 'content']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'topic', 'created_at', 'published']
    list_editable = ['published']
    search_fields = ['title', 'author', 'content']
    list_filter = ['created_at', 'topic', 'published']
    list_per_page = 10
    form = ArticleFormAdmin

    save_on_top = True
    fields = ['title', 'slug', 'topic', 'author', 'published', 'content']
    prepopulated_fields = {'slug': ('title',)}


class ArticleInline(admin.StackedInline):
    model = Article
    extra = 0
    show_change_link = True
    fields = ['title', 'slug', 'topic', 'published', 'author', 'content']
    prepopulated_fields = {'slug': ('title',)}
    form = ArticleFormAdmin

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).none()

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'created_at']
    search_fields = ['title', 'category']
    list_editable = ['category']
    list_filter = ['category', 'author', 'created_at']
    list_per_page = 10

    save_on_top = True
    fields = ['title', 'slug', 'category', 'author']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ArticleInline]


class TopicInline(admin.StackedInline):
    model = Topic
    extra = 0
    show_change_link = True
    fields = ['title', 'slug', 'category', 'author']
    prepopulated_fields = {'slug': ('title',)}

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).none()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at']
    search_fields = ['title']
    list_filter = ['author', 'created_at']
    list_per_page = 10


    save_on_top = True
    fields = ['title', 'slug', 'author']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [TopicInline]

admin.site.site_header = "Панель администратора базы знаний"
admin.site.register(ArticleChunk)