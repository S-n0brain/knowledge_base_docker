from typing import Any
from django import forms
from ckeditor_uploader.fields import RichTextUploadingFormField
from django.core.validators import MinLengthValidator
from slugify import slugify
from .models import Article, Category, Topic
import datetime

class ArticleForm(forms.ModelForm):
    content = RichTextUploadingFormField(label='Содержание статьи', required=False)

    def __init__(self, *args, **kwargs):
        topic_slug = kwargs.pop('topic_slug', None)
        super().__init__(*args, **kwargs)
        self.fields['published'].initial = True
        if topic_slug and Topic.objects.filter(slug=topic_slug).exists():
            self.fields['topic'].initial = Topic.objects.get(slug=topic_slug)
            self.fields['topic'].disabled = True


        self.fields['topic'].empty_label = 'Нет темы' # type: ignore
        self.fields['title'].validators += [MinLengthValidator(1)]

    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Это обязательное поле.")
        slug = slugify(title, lowercase=True)
        if Article.objects.filter(slug=slug).exists():
            raise forms.ValidationError("Статья с таким URL адресом уже существует.")
        self.cleaned_data['slug'] = slug
        return title

    def is_valid(self) -> bool:
        for field in self.fields:
            if field != 'content':
                if self.errors.get(field):
                    self.fields[field].widget.attrs['class'] += ' is-invalid'
        return super().is_valid()

    class Meta:
        model = Article
        fields = ['title', 'topic', 'published', 'content']

        widgets = {
            'title': forms.widgets.TextInput(attrs={'class': 'form-control my-2'}),
            'topic': forms.widgets.Select(attrs={'class': 'form-select my-2'}),
            'published': forms.widgets.CheckboxInput(attrs={'class': 'form-check-input my-2'}),
        }


class ArticleUpdateForm(ArticleForm):
    def clean_title(self):
        old_slug = self.instance.slug
        old_title = self.instance.title
        title_current = self.cleaned_data.get('title', '').strip()
        if not title_current:
            raise forms.ValidationError("Это обязательное поле.")
        if title_current != old_title:
            slug = slugify(title_current, lowercase=True)
            if Article.objects.filter(slug=slug).exists():
                raise forms.ValidationError("Статья с таким URL адресом уже существует.")
            self.cleaned_data['slug'] = slug
        else:
            self.cleaned_data['slug'] = old_slug
        return title_current


class CategoryForm(forms.ModelForm):
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Это обязательное поле.")
        slug = slugify(title, lowercase=True)
        if Category.objects.filter(slug=slug).exists():
            raise forms.ValidationError("Категория с таким URL адресом уже существует.")
        self.cleaned_data['slug'] = slug
        return title

    class Meta:
        model = Category
        fields = ['title']
        widgets = {
            'title': forms.widgets.TextInput(attrs={'class': 'form-control my-2'}),
        }


class TopicForm(forms.ModelForm):
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Это обязательное поле.")
        slug = slugify(title, lowercase=True)
        if Topic.objects.filter(slug=slug).exists():
            raise forms.ValidationError("Тема с таким URL адресом уже существует.")
        self.cleaned_data['slug'] = slug
        return title
    
    class Meta:
        model = Topic
        fields = ['title']
        widgets = {
            'title': forms.widgets.TextInput(attrs={'class': 'form-control my-2'}),
        }


class AddTopicForm(TopicForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(),
                                       label='Раздел',
                                       empty_label="Выберите раздел",
                                      widget=forms.Select(attrs={'class': 'form-select my-2'}))
    class Meta:
        model = Topic
        fields = ['title', 'category']
        widgets = {
            'title': forms.widgets.TextInput(attrs={'class': 'form-control my-2'}),
        }


class SearchArticleForm(forms.Form):
    query = forms.CharField(max_length=100,
                            widget=forms.TextInput(attrs={'class': 'form-control my-2 rounded-pill',
                                                          'type': "search", 'placeholder': "Поиск", 'aria-label': "Поиск"}), required=False)
    category = forms.ModelMultipleChoiceField(queryset=Category.objects.all(),
                                       widget=forms.CheckboxSelectMultiple(attrs={'class': 'mt-2 filter', 'type': "checkbox"}), required=False)
    topic = forms.ModelMultipleChoiceField(queryset=Topic.objects.all(),
                                    widget=forms.CheckboxSelectMultiple(attrs={'class': ' mt-2 filter', 'type': "checkbox"}), required=False)
    date_created_from = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control form-control-sm mt-2 filter', 'type': 'date',
                                                                      'min': '2020-01-01', 'max': datetime.date.today()}), required=False)
    date_created_to = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control form-control-sm mt-2 filter', 'type': 'date',
                                                                      'min': '2020-01-01', 'max': datetime.date.today()}), required=False)