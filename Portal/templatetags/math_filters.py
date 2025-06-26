from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def add_decimal(value, arg):
    """Add decimal values"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0