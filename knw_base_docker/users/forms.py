import datetime
from typing import Any
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.db.models import Q

from .models import EmailConfirmation
from django.contrib.auth.models import Group
from knowledge_base.settings import ADMIN_CREATION_CODE

class IsValidForm(forms.Form):
    def is_valid(self) -> bool:
        if self.errors:
            for field in self.fields:
               if self.errors.get(field):
                   self.fields[field].widget.attrs['class'] += ' is-invalid'
        return super().is_valid()


class LoginUserForm(AuthenticationForm):
    username = forms.CharField(label='Логин',
                               widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Пароль',
                               widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    

    def is_valid(self) -> bool:
        if self.errors:
            for field in self.fields:
                self.fields[field].widget.attrs['class'] += ' is-invalid'
        return super().is_valid()

    class Meta:
        model = get_user_model()
        fields = ['username', 'password']


class UserRegistrationForm(UserCreationForm, IsValidForm):
    username = forms.CharField(label="Логин", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    is_admin = forms.BooleanField(label="Администратор", required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is_admin'}))
    admin_code = forms.CharField(label="Код администратора", required=False,
                                 widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'admin_code'}),
                                 validators=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

        for field in self.fields:
            if self.fields[field].required:
                self.fields[field].label = "* " + self.fields[field].label # type: ignore

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and (get_user_model().objects.filter(email=email).exists() or EmailConfirmation.objects.filter(Q(confirm_email=email) | Q(email_in_process_confirm=email)).exists()):
            raise forms.ValidationError("Email уже зарегистрирован.")
        return email

    def clean_admin_code(self):
        is_admin = self.cleaned_data.get('is_admin')
        admin_code = self.cleaned_data.get('admin_code')
        if is_admin:
            if not admin_code:
                raise forms.ValidationError("Введите код администратора.")
            if admin_code != ADMIN_CREATION_CODE:
                raise forms.ValidationError("Неверный код администратора.")
        return admin_code

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('is_admin') and self.cleaned_data.get('admin_code') == ADMIN_CREATION_CODE:
            group = Group.objects.get(name='admin')
            user.is_staff = True
        else:
            group = Group.objects.get(name='intern')
        if commit:
            user.save()
            user.groups.add(group)
        return user

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
    
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserPasswordChangeForm(PasswordChangeForm, IsValidForm):
    old_password = forms.CharField(label='Старый пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password1 = forms.CharField(label='Новый пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(label='Повторите новый пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = get_user_model()
        fields = ['old_password', 'new_password1', 'new_password2']


class UserPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control',
                                                                           "autocomplete": "email"}))
    

class UserPasswordResetConfirmForm(SetPasswordForm, IsValidForm):
    new_password1 = forms.CharField(label='Новый пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(label='Повторите новый пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = get_user_model()
        fields = ['new_password1', 'new_password2']


class UserProfileForm(forms.ModelForm, IsValidForm):
    photo = forms.ImageField(label='Фото', required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(label='Имя', widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label='Фамилия', widget=forms.TextInput(attrs={'class': 'form-control'}))
    date_birth = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control w-25"}),
                                 label='Дата рождения',required=False)
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_birth'].widget.attrs['min'] = '1900-01-01'
        self.fields['date_birth'].widget.attrs['max'] = datetime.date.today()

    def clean_photo(self) -> Any:
        photo = self.cleaned_data.get('photo')
        if photo and self.instance.photo:
            self.cleaned_data['old_photo'] = self.instance.photo
        return photo

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if self.instance.photo:
            cleaned_data['photo_path'] = self.instance.photo.path
        return cleaned_data

    class Meta:
        model = get_user_model()
        fields = ['photo', 'first_name', 'last_name', 'date_birth']

class UserConfirmEmailForm(IsValidForm, forms.Form):
    email = forms.EmailField(label='Подтверждение адреса эл. почты', widget=forms.EmailInput(attrs={'class': 'form-control', 'id': 'confirm_email_field',
                                                                                                    'placeholder': 'Для подтверждения введите email '}))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("instance")
        super().__init__(*args, **kwargs)


    def clean_email(self):
        new_email = self.cleaned_data.get('email')
        old_email = self.user.email
        if old_email == new_email:
            self.cleaned_data['old_email'] = old_email
        if new_email and EmailConfirmation.objects.filter(confirm_email=new_email, is_confirmed=True).exists():
            raise forms.ValidationError("Email уже подтверждён")
        if new_email and get_user_model().objects.filter(email=new_email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Email уже зарегистрирован.")
        return new_email
