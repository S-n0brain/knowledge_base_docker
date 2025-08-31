from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView, PasswordChangeDoneView, PasswordResetDoneView, PasswordResetCompleteView

app_name = 'users'
urlpatterns = [
    path('login/', views.LoginUser.as_view(), name='login'),
    path('logout/', LogoutView.as_view(
        next_page='users:login'
    ), name='logout'),
    path('register/', views.RegisterUser.as_view(), name='register'),
    path('profile/', views.UserProfile.as_view(), name='profile'),
    path('confirm-email/', views.UserConfirmEmailView.as_view(), name='confirm_email'),
    path('confirm-email/done', views.UserEmailConfirmationDoneView.as_view(), name='confirm_email_done'),
    path('confirm-email/<uuid:token>/', views.UserEmailConfirmationConfirmView.as_view(), name='email_confirmation_confirm'),
    path('confirm-email/error/', views.UserEmailConfirmationErrorView.as_view(), name='email_confirmation_error'),
    path('confirm-email/complete/', views.UserEmailConfirmationCompleteView.as_view(), name='email_confirmation_complete'),

    path('password-change/', views.UserPasswordChange.as_view(), name='password_change'),
    path('password-change/done/', PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password-reset/', views.UserPasswordReset.as_view(), name='password_reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),
    path('password_reset/<uidb64>/<token>/', views.UserPasswordResetConfirm.as_view(),
         name='password_reset_confirm'),
    path('password_reset_complete/', PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete')
]