# clinic/templatetags/clinic_extras.py

from django import template

register = template.Library()

@register.filter
def can_view(file, user):
    return file.can_view_by(user)