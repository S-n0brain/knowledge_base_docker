import re
from django import template
from ..models import Category, Topic, Article
from ..forms import CategoryForm, SearchArticleForm, AddTopicForm

register = template.Library()

@register.simple_tag
def get_categories():
    return Category.objects.all()

@register.simple_tag
def get_topics(category):
    return Topic.objects.filter(category=category).order_by("title")

@register.simple_tag
def get_article(topic):
    return Article.objects.filter(topic=topic, published=True).order_by("title")

@register.simple_tag
def get_last_articles():
    return Article.objects.filter(published=True).order_by("-updated_at")[:4]


@register.inclusion_tag("knowledge_base_app/add_category_form.html")
def add_category_form():
    cat_form = CategoryForm()
    topic_form = AddTopicForm()
    return {"form_add_category": cat_form, "form_add_topic": topic_form}

@register.simple_tag
def get_search_form():
    form = SearchArticleForm()
    return form
