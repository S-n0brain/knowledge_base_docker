from django.urls import path, re_path
from . import views

app_name = 'knowledge_base_app'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('article/<slug:slug>/', views.ArticleDetailView.as_view(), name='article-detail'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('topic/<slug:slug>/', views.TopicDetailView.as_view(), name='topic-detail'),  
    re_path(r'^article_add/(?P<topic_slug>[-\w]+)?/?$', views.ArticleAddView.as_view(), name='article-add'),
    path('article_update/<slug:slug>/', views.ArticleUpdateView.as_view(), name='article-update'),
    path('add_category/', views.add_category, name='category-add'),
    path('add_topic/', views.add_topic, name='topic-add'),
    path('article_search/', views.ArticleSearchView.as_view(), name='article-search'),
]
