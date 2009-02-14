import re
from google.appengine.ext import webapp
 
register = webapp.template.create_template_register()
 
# turn @nicknames into html links for the twitter page for that user
def twitter_at_linkify(s):
  p = re.compile('(@)([\w]+)', re.MULTILINE)
  return p.sub(r'<a href="http://twitter.com/\2" >\1\2</a>',s)
register.filter(twitter_at_linkify)

# converts a list to a comma separated string with 'and' as the last separator
def inline_list(l, sort=True, separator=', ', last_separator=' and '):
  if(sort): l.sort()
  list_size = len(l)
  return  separator.join(l[:list_size-1]) + (last_separator if list_size > 1 else '') +l[list_size-1]
register.filter(inline_list)
  