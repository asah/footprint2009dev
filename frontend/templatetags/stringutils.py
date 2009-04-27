# http://w.holeso.me/2008/08/a-simple-django-truncate-filter/
# with modifications to work in AppEngine:
#   http://4.flowsnake.org/archives/459

from google.appengine.ext import webapp

def truncate_chars(value, max_length):
  if len(value) > max_length:
    truncated_value = value[:max_length]
    if value[max_length + 1] != ' ':
      # TODO: Make sure that only whitespace in the data records
      #     is ascii spaces.
      right_index = truncated_value.rfind(' ')
      ellipsis = ' ...'
      MAX_CHARS_TO_CLIP = 40
      if right_index < max_length - MAX_CHARS_TO_CLIP:
        right_index = max_length - MAX_CHARS_TO_CLIP
        ellipsis = '...'  # No separating space
      truncated_value = truncated_value[:right_index]
    return  truncated_value + ellipsis
  return value

register = webapp.template.create_template_register()
register.filter('truncate_chars', truncate_chars)
