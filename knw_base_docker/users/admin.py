from typing import Any
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.http import HttpRequest
from users.models import EmailConfirmation, User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

User = get_user_model()


@admin.register(EmailConfirmation)
class EmailConfirmationAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_in_process_confirm', 'confirm_email', 'is_confirmed']
    search_fields = ['user__username', 'email_in_process_confirm', 'confirm_email']
    list_filter = ['is_confirmed']

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, label='Имя')
    last_name = forms.CharField(max_length=100, label='Фамилия')

    class Meta(UserCreationForm.Meta):  # type: ignore
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name',)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', "last_name", "first_name", "is_staff"]
    list_display_links = ['username', ]
    list_editable = ["last_name", "first_name", "is_staff"]
    save_on_top = True
    add_form = CustomUserCreationForm

    def save_related(self, request: HttpRequest, form: forms.ModelForm, formsets: forms.BaseModelFormSet, change: bool) -> None:
        # Сохранение связанных объектов
        super().save_related(request, form, formsets, change)
        if form.instance.is_staff:
            form.instance.groups.add(Group.objects.get(name='admin'))
        else:
            form.instance.groups.remove(Group.objects.get(name='admin'))
        return form.instance

    fieldsets =  (
        ('', {'fields': ('photo', 'date_birth')}),
    ) + UserAdmin.fieldsets # type: ignore

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", 
                       "first_name", "last_name"),
        }),
    )


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)