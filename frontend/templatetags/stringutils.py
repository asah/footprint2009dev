# http://w.holeso.me/2008/08/a-simple-django-truncate-filter/
# with modifications to work in AppEngine:
#   http://4.flowsnake.org/archives/459

from google.appengine.ext import webapp

def truncate_chars(value, max_length):
    if len(value) > max_length:
        truncd_val = value[:max_length]
        if value[max_length+1] != " ":
            truncd_val = truncd_val[:truncd_val.rfind(" ")]
        return  truncd_val + " ..."
    return value

register = webapp.template.create_template_register()
register.filter('truncate_chars', truncate_chars)
