from django import template

# Registering the template library
register = template.Library()

@register.filter
def mul(value, arg):
    return value * arg

