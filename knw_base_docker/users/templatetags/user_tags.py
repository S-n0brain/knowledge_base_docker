from django import template


register = template.Library()

@register.filter
def get_user_group(user):
    if user.is_superuser:
        return "Главный администратор"
    elif user.groups.filter(name='admin').exists():
        return "Администратор"
    return "Пользователь"