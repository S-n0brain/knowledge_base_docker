from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from ckeditor_uploader.fields import RichTextUploadingField
from django.utils.html import strip_tags
from pgvector.django import VectorField

from openai import OpenAI
from knowledge_base.settings import API_GPT_KEY

class PublishedArticleManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(published=True).select_related('topic')

class Article(models.Model):
    BASE_URL_MODAL = "https://api.proxyapi.ru/openai/v1"

    title = models.CharField(max_length=250, verbose_name="Название статьи")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL-адрес статьи")
    topic = models.ForeignKey(to="Topic", on_delete=models.CASCADE, related_name="articles", verbose_name="Тема статьи")
    author = models.ForeignKey(to=get_user_model(), on_delete=models.CASCADE, related_name="articles", verbose_name="Автор статьи")
    content = RichTextUploadingField(blank=True, verbose_name="Содержимое статьи")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    published = models.BooleanField(default=False, verbose_name="Опубликовано")

    objects = models.Manager()
    published_manager = PublishedArticleManager()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("knowledge_base_app:article-detail", kwargs={"slug": self.slug})

    def get_plain_content(self):
        return strip_tags(self.content)
    
    @staticmethod
    def chunk_text(text: str, chunk_size=500):
        # Разделение текста на фрагменты заданного размера
        words = text.split()
        for i in range(0, len(words), chunk_size):
            yield ' '.join(words[i:i + chunk_size])

    def create_article_chunks(self):
        self.chunks.all().delete()  # type: ignore
        plain_content = self.get_plain_content()
        try:
            client = OpenAI(api_key=API_GPT_KEY, base_url=self.BASE_URL_MODAL)
        except Exception:
            embedding = None
            ArticleChunk.objects.create(article=self, text=plain_content, embedding=embedding)
        else:
            for chunk in self.chunk_text(plain_content):
                try:
                    response = client.embeddings.create(
                        input=chunk,
                        model="text-embedding-3-small"
                    )
                    embedding = response.data[0].embedding
                except Exception as e:
                    embedding = None
                    print(f"Ошибка при создании эмбеддинга: {e}")
                ArticleChunk.objects.create(article=self, text=chunk, embedding=embedding)

    def save(self, *args, **kwargs):
        # Сохранение модели с генерацией векторного представления
        try:
            old_content = Article.objects.get(pk=self.pk).content
        except Article.DoesNotExist:
            old_content = None
        super().save(*args, **kwargs)
        if not self.pk or (self.content != old_content):
            self.create_article_chunks()
            
    class Meta:
        ordering = ['title']
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"
        indexes = [
            models.Index(fields=['title']),
        ]
        

class Topic(models.Model):
    title = models.CharField(max_length=250, verbose_name="Название темы")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL-адрес темы")
    category = models.ForeignKey(to="Category", on_delete=models.CASCADE, related_name="topics", verbose_name="Раздел темы")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.title
    
    def has_published_articles(self):
        return self.articles.filter(published=True) # type: ignore

    def get_absolute_url(self):
        return reverse("knowledge_base_app:topic-detail", kwargs={"slug": self.slug})

    class Meta:
        ordering = ['title']
        verbose_name = "Тема"
        verbose_name_plural = "Темы"


class Category(models.Model):
    title = models.CharField(max_length=250, verbose_name="Название раздела")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL-адрес раздела")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("knowledge_base_app:category-detail", kwargs={"slug": self.slug})

    class Meta:
        ordering = ['title']
        verbose_name = "Раздел"
        verbose_name_plural = "Разделы"

class ArticleChunk(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="chunks", verbose_name="Статья")
    embedding = VectorField(dimensions=1536, null=True, verbose_name="Векторное представление", default=None)
    text = models.TextField(blank=True, verbose_name="Текстовый фрагмент")
    
    class Meta:
        verbose_name = "Часть статьи для векторного представления"
        verbose_name_plural = "Части статьи для векторного представления"
