# clinic/templatetags/date_extras.py
from django import template
from datetime import datetime, timedelta

register = template.Library()

@register.filter
def add_days(value, days):
    """Добавляет N дней к дате"""
    if isinstance(value, str):
        try:
            date_obj = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value
    else:
        date_obj = value
    new_date = date_obj + timedelta(days=int(days))
    return new_date.strftime('%Y-%m-%d')

@register.filter
def make_list(value):
    """Превращает строку в список символов"""
    return list(str(value))