import datetime
import os
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.db.models.base import Model as Model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetView, PasswordResetConfirmView
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, FormView, TemplateView, UpdateView
from knowledge_base import settings
from .models import EmailConfirmation
from .forms import LoginUserForm, UserConfirmEmailForm, UserPasswordChangeForm, UserPasswordResetConfirmForm, UserPasswordResetForm, UserProfileForm, UserRegistrationForm
from knowledge_base.settings import DEFAULT_USER_IMAGE
from django.contrib.auth.mixins import LoginRequiredMixin

class LoginUser(LoginView):
    form_class = LoginUserForm
    template_name = 'users/login.html'
    extra_context = {'title': 'Вход'}
    next_page = reverse_lazy('knowledge_base_app:index')


class RegisterUser(CreateView):
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    extra_context = {'title': "Регистрация"}
    success_url = reverse_lazy('users:login')


class UserPasswordChange(PasswordChangeView):
    form_class = UserPasswordChangeForm
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('users:password_change_done')
    extra_context = {'title': 'Смена пароля'}


class UserPasswordReset(PasswordResetView):
    form_class = UserPasswordResetForm
    template_name = 'users/password_reset.html'
    success_url = reverse_lazy('users:password_reset_done')
    extra_context = {'title': 'Сброс пароля'}
    email_template_name = 'users/password_reset_email.html'
    html_email_template_name = 'users/password_reset_email.html'


class UserPasswordResetConfirm(PasswordResetConfirmView):
    form_class = UserPasswordResetConfirmForm
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')
    extra_context = {'title': 'Сброс пароля'}


class UserProfile(LoginRequiredMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:profile')
    extra_context = {'title': 'Профиль', 'default_user_image': DEFAULT_USER_IMAGE}

    def get_object(self, queryset: QuerySet=None) -> Model: # type: ignore
        return self.request.user # type: ignore

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['email_form'] = UserConfirmEmailForm(instance=self.request.user)
        context['title'] = 'Профиль пользователя'
        return context
    
    def form_valid(self, form):
        if form.cleaned_data.get('old_photo'):
            old_photo = form.cleaned_data['old_photo']
            if old_photo is not form.instance.photo:
                if os.path.exists(old_photo.path):
                    try:
                        os.remove(old_photo.path)
                    except FileNotFoundError:
                        pass
        if form.cleaned_data['photo'] == False and form.cleaned_data.get('photo_path'):
            if os.path.exists(form.cleaned_data['photo_path']):
                try:
                    os.remove(form.cleaned_data['photo_path'])
                except FileNotFoundError:
                    form.instance.photo = None
        return super().form_valid(form)


class UserConfirmEmailView(LoginRequiredMixin, FormView):
    form_class = UserConfirmEmailForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:confirm_email_done')

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email_form'] = self.get_form_class()(data=self.request.POST, instance=self.request.user)
        return context
    
    def form_invalid(self, form) -> HttpResponse:
        return redirect('users:profile')


    def form_valid(self, form):
        user_email = form.user.email
        if user_email:
            # Текуший email пользователя не подтвержден
            if form.cleaned_data.get('old_email'):
                # Подтверждаем текущий email
                email = user_email
            else:
                email = form.cleaned_data.get('email')

            if EmailConfirmation.objects.filter(user=form.user).exists():
                try:
                    confirmation = EmailConfirmation.objects.get(user=form.user)
                except (EmailConfirmation.DoesNotExist, EmailConfirmation.MultipleObjectsReturned):
                    return redirect('users:email_confirmation_error')
            else:
                # Удалить или что то сделать если пользователь уже есть в бд
                confirmation = EmailConfirmation(
                    user=form.user,
                    confirm_email=''
                )
            confirmation.email_in_process_confirm = email
            confirm_url = self.request.build_absolute_uri(
                    reverse('users:email_confirmation_confirm', kwargs={'token': confirmation.token})
                )
            try:
                send_mail(
                    subject='Подтверждение email',
                    message=f'Перейдите по ссылке для подтверждения email: {confirm_url}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email]
                )
            except Exception:
                return redirect('users:email_confirmation_error')
            confirmation.save()
        return super().form_valid(form)


class UserEmailConfirmationDoneView(LoginRequiredMixin, TemplateView):
    template_name = 'users/email_confirmation_done.html'


class UserEmailConfirmationConfirmView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        confirmation = get_object_or_404(EmailConfirmation, token=kwargs.get('token'))
        if not self.check_time_limit(confirmation) or EmailConfirmation.objects.filter(confirm_email=confirmation.confirm_email, is_confirmed=True).exists():
            return redirect("users:email_confirmation_error")
        try:
            EmailConfirmation.objects.filter(email_in_process_confirm=confirmation.email_in_process_confirm).exclude(user=confirmation.user).delete()
        except Exception:
            pass
        if not EmailConfirmation.objects.filter(confirm_email=confirmation.email_in_process_confirm, is_confirmed=True).exists():
            confirmation.confirm_email = confirmation.email_in_process_confirm
            confirmation.email_in_process_confirm = ''
            confirmation.is_confirmed = True # type: ignore
            confirmation.save()
            user = confirmation.user
            user.email = confirmation.confirm_email # type: ignore
            user.save()
            return redirect('users:email_confirmation_complete')
        return redirect("users:email_confirmation_error")

    def check_time_limit(self, confirmation: EmailConfirmation) -> bool:
        # Проверяем, не истек ли срок действия подтверждения email
        if confirmation.created_at + datetime.timedelta(hours=1) < datetime.datetime.now(datetime.timezone.utc):
            if not confirmation.confirm_email:
                confirmation.delete()
            return False
        return True


class UserEmailConfirmationErrorView(TemplateView):
    template_name = 'users/email_confirmation_error.html'

class UserEmailConfirmationCompleteView(TemplateView):
    template_name = 'users/email_confirmation_complete.html'