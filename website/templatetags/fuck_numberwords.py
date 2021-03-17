from django import template

from ..helpers import replaceTextnumberWithNumber

register = template.Library()

@register.filter(name='fuck_numberwords')
def fuck_numberwords(text):
    return replaceTextnumberWithNumber(text)
