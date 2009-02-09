import re
from google.appengine.ext import webapp
 
register = webapp.template.create_template_register()
 
# turn @nicknames into html links for the twitter page for that user
def twitter_at_linkify(s):
  p = re.compile('(@)([\w]+)', re.MULTILINE)
  return p.sub(r'<a href="http://twitter.com/\2" >\1\2</a>',s)

register.filter(twitter_at_linkify)


