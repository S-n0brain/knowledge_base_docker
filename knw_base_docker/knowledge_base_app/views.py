from typing import Any
from django.core.cache import cache
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView
from .forms import AddTopicForm, ArticleForm, ArticleUpdateForm, CategoryForm, SearchArticleForm, TopicForm
from .models import Article, Category, Topic
from django.views.generic.edit import ModelFormMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from .documents import ArticleDocument
from django.core.exceptions import PermissionDenied

@permission_required('knowledge_base_app.add_category', raise_exception=True)
def add_category(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.slug = form.cleaned_data['slug']
            category.save()
            return redirect('knowledge_base_app:category-detail', slug=category.slug)
    return redirect(request.META.get('HTTP_REFERER', 'knowledge_base_app:index')) # redirect(request.POST.get('next', 'knowledge_base_app:index'))

@permission_required('knowledge_base_app.add_topic', raise_exception=True)
def add_topic(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AddTopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.slug = form.cleaned_data['slug']
            topic.save()
            return redirect('knowledge_base_app:topic-detail', slug=topic.slug)
    return redirect(request.META.get('HTTP_REFERER', 'knowledge_base_app:index'))

def get_cached_categories():
    key = "categories_with_topics_articles"
    categories = cache.get(key)
    if categories is None:
        categories = Category.objects.prefetch_related("topics__articles").all()
        cache.set(key, categories, 60*3)  # кэш на 3 минуты
    return categories

class IndexView(TemplateView):
    title = "Главная страница"
    welcome_message = "Добро пожаловать в базу знаний"
    about_message = "В базе знаний доступны статьи по различным темам."
    extra_context = {
        'title': title,
        'welcome_message': welcome_message,
        'about_message': about_message,
    }
    template_name = 'knowledge_base_app/index.html'

    @staticmethod
    def get_cached_last_articles():
        key = "last_articles"
        last_articles = cache.get(key)
        if last_articles is None:
            last_articles = Article.published_manager.order_by('-updated_at').select_related('topic')[:4]
            cache.set(key, last_articles, 60*3)  # кэш на 3 минуты
        return last_articles

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context =  super().get_context_data(**kwargs)
        context['categories'] = get_cached_categories() #Category.objects.prefetch_related('topics__articles')
        context['last_articles'] = self.get_cached_last_articles() # type: ignore
        return context

class ArticleDetailView(DetailView):
    model = Article
    context_object_name = 'article_curr'
    template_name = 'knowledge_base_app/article_detail.html'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['category_curr'] = self.get_object().topic.category # type: ignore
        context['topic_curr'] = self.get_object().topic # type: ignore
        context['categories'] = get_cached_categories() # Category.objects.prefetch_related('topics__articles')
        return context
    
    def post(self, request, *args, **kwargs):
        if request.POST.get("delete"):
            if self.request.user.has_perm('knowledge_base_app.delete_article'):
                self.object = self.get_object()
                self.object.delete()
                return redirect('knowledge_base_app:topic-detail', slug=self.object.topic.slug) # type: ignore
            else:
                raise PermissionDenied
        return redirect('knowledge_base_app:index')
    

class CategoryDetailView(ModelFormMixin, DetailView):
    model = Category
    context_object_name = 'category_curr'
    template_name = 'knowledge_base_app/category_detail.html'
    form_class = CategoryForm
    topic_form_class = TopicForm

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['categories'] = get_cached_categories() #Category.objects.prefetch_related('topics__articles')
        context['form'] = self.get_form_class()(instance=self.get_object())
        context['topic_form'] = self.topic_form_class()
        return context
    
    def post(self, request, *args, **kwargs):
        # Обработка удаления категории
        if request.POST.get("delete_cat"):
            if not request.user.has_perm('knowledge_base_app.delete_category'):
                raise PermissionDenied
            self.object = self.get_object()
            self.object.delete()
            return redirect('knowledge_base_app:index')
        # Обработка удаления темы
        elif request.POST.get("delete_topic"):
            if not request.user.has_perm('knowledge_base_app.delete_topic'):
                raise PermissionDenied
            topic_slug = request.POST.get('delete_topic')
            topic = get_object_or_404(Topic, slug=topic_slug)
            topic.delete()
            return redirect('knowledge_base_app:category-detail', slug=self.get_object().slug) # type: ignore
        # Обработка редактирования категории
        elif request.POST.get("edit_cat"):
            if not request.user.has_perm('knowledge_base_app.change_category'):
                raise PermissionDenied
            form = self.get_form_class()(request.POST, instance=self.get_object())
            self.object = self.get_object()
            if form.is_valid():
                self.object = form.save(commit=False)
                self.object.slug = form.cleaned_data['slug']
                form.save()
                return redirect('knowledge_base_app:category-detail', slug=self.object.slug) # type: ignore
            return self.form_invalid(form)
        elif request.POST.get("add_topic"):
            if not request.user.has_perm('knowledge_base_app.add_topic'):
                raise PermissionDenied
            form = self.topic_form_class(request.POST)
            if form.is_valid():
                topic = form.save(commit=False)
                topic.category = self.get_object()
                topic.slug = form.cleaned_data['slug']
                topic.save()
                return  redirect('knowledge_base_app:category-detail', slug=topic.category.slug) # type: ignore
            return self.get(request, *args, **kwargs)


class TopicDetailView(ModelFormMixin, DetailView):
    model = Topic
    form_class = TopicForm
    context_object_name = 'topic_curr'
    template_name = 'knowledge_base_app/topic_detail.html'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['categories'] = get_cached_categories() # Category.objects.prefetch_related('topics__articles')
        context['form'] = self.get_form_class()(instance=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        # Обработка удаления статьи
        if request.POST.get("delete_article"):
            if not request.user.has_perm('knowledge_base_app.delete_article'):
                raise PermissionDenied
            article_slug = request.POST.get('delete_article')
            article = get_object_or_404(Article, slug=article_slug)
            article.delete()
            return redirect('knowledge_base_app:topic-detail', slug=self.get_object().slug) # type: ignore
        # Обработка удаления темы
        elif request.POST.get("delete_topic"):
            if not request.user.has_perm('knowledge_base_app.delete_topic'):
                raise PermissionDenied
            self.object = self.get_object()
            category_slug = self.object.category.slug # type: ignore
            self.object.delete()
            return redirect('knowledge_base_app:category-detail', slug=category_slug) # type: ignore
        # Обработка редактирования темы
        elif request.POST.get("edit_topic"):
            if not request.user.has_perm('knowledge_base_app.change_topic'):
                raise PermissionDenied
            form = self.get_form_class()(request.POST, instance=self.get_object())
            self.object = self.get_object() 
            if form.is_valid():
                self.object = form.save(commit=False)
                self.object.slug = form.cleaned_data['slug']
                self.object.category = self.get_object().category # type: ignore
                self.object.save()
                return redirect('knowledge_base_app:topic-detail', slug=self.object.slug) 
            return self.form_invalid(form)


class ArticleAddView(PermissionRequiredMixin, CreateView):
    form_class = ArticleForm
    template_name = 'knowledge_base_app/article_add_form.html'
    permission_required = 'knowledge_base_app.add_article'

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        path = self.request.get_full_path()
        slug = path.split('/')[-1]
        kwargs['topic_slug'] = slug if slug not in ("", "add") else None
        return kwargs 

    def form_valid(self, form):
        article: Article = form.save(commit=False)
        article.author = self.request.user # type: ignore
        article.slug = form.cleaned_data['slug']
        article.save()
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse_lazy('knowledge_base_app:article-detail', kwargs={"slug": self.object.slug}) # type: ignore

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавление и редактирование статьи'
        context["categories"] = get_cached_categories() # Category.objects.prefetch_related('topics__articles')
        return context


class ArticleUpdateView(PermissionRequiredMixin, UpdateView):
    model = Article
    form_class = ArticleUpdateForm
    template_name = 'knowledge_base_app/article_add_form.html'
    permission_required = 'knowledge_base_app.change_article'

    def form_valid(self, form):
        article: Article = form.save(commit=False)
        article.author = self.request.user # type: ignore
        article.slug = form.cleaned_data['slug']
        article.save()
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse_lazy('knowledge_base_app:article-detail', kwargs={"slug": self.object.slug}) # type: ignore

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавление и редактирование статьи'
        context["categories"] = get_cached_categories() # Category.objects.prefetch_related('topics__articles')
        return context
    

class ArticleSearchView(FormView, ListView):
    model = Article
    template_name = 'knowledge_base_app/search.html'
    context_object_name = 'articles'
    form_class = SearchArticleForm

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['form_search'] = self.get_form_class()(self.request.GET)
        context["categories"] = get_cached_categories() # Category.objects.prefetch_related('topics__articles')
        context['title'] = 'Поиск статей'
        return context
    
    def get_queryset(self) -> QuerySet[Any]:
        queryset = Article.published_manager.all()
        form = self.get_form_class()(self.request.GET)
        if form.is_valid():
            query = form.cleaned_data.get('query', '').strip()
            category = form.cleaned_data.get('category')
            topic = form.cleaned_data.get('topic')
            date_created_from = form.cleaned_data.get('date_created_from')
            date_created_to = form.cleaned_data.get('date_created_to')
            if query:
                queryset = self.search_in_elastic(query, queryset)
            if category:
                queryset = queryset.filter(topic__category__in=category)
            if topic:
                queryset = queryset.filter(topic__in=topic)
            if date_created_from:
                queryset = queryset.filter(created_at__gte=date_created_from)
            if date_created_to:
                queryset = queryset.filter(created_at__lte=date_created_to)
        return queryset.select_related('topic', 'author')

    def search_in_elastic(self, query, queryset):
        try:
            s = ArticleDocument.search().query(
                "multi_match",
                query=query,
                fields=["title^2", "content", "topic"],
                fuzziness="AUTO",
                type="best_fields",
            ) # highlight("content", "title", "topic", fragment_size=100)
            s = s.sort("_score")
            queryset = s.to_queryset().filter(id__in=queryset.values_list("id", flat=True))
        except Exception as e:
            print(f'Ошибка при выполнении запроса к Elasticsearch:\n{e}')
            return queryset
        return queryset