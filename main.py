# QuoteURL - URL for Twitter Dialogues
#
# Copyright (c) 2008, Fabricio Zuardi
# All rights reserved.
#  
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of the author nor the names of its contributors
#     may be used to endorse or promote products derived from this
#     software without specific prior written permission.
#  
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
__author__ = ('Fabricio Zuardi', 'fabricio@fabricio.org', 'http://fabricio.org')

import os
import cgi
import wsgiref.handlers
import urllib

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class Dialogue(db.Model):
  title             = db.StringProperty()
  alias             = db.StringProperty()
  status_id_list    = db.StringListProperty()
  authors           = db.StringProperty()
  author_list       = db.StringListProperty()
  quoter            = db.UserProperty()
  quoter_ip         = db.StringProperty()
  quoter_user_agent = db.StringProperty()
  created_date      = db.DateTimeProperty(auto_now_add=True)
  content_json      = db.TextProperty()

class MainPage(webapp.RequestHandler):
  def get(self):
    template_values = {}
    path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
    self.response.out.write(template.render(path, template_values))

class CreateQuote(webapp.RequestHandler):
  def post(self):
    status_list = cgi.escape(self.request.get('statuses')).replace(',',' ').split()
    authors_list = cgi.escape(self.request.get('authors')).replace(',',' ').split()
    content_json = cgi.escape(self.request.get('content_json'))
    # status_list.sort()
    user = users.get_current_user()
    ip = os.environ['REMOTE_ADDR']
    ua = os.environ['HTTP_USER_AGENT']
    content = []
    dialogue = Dialogue()
    dialogue.title = ', '.join(status_list)
    dialogue.status_id_list = status_list
    dialogue.quoter = user
    dialogue.quoter_ip = ip
    dialogue.quoter_user_agent = ua
    dialogue.alias = None
    dialogue.authors = None
    dialogue.author_list = []
    dialogue.content_json = content_json
    template_values = {
      'dialogue'    : dialogue
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/show.html')
    # self.response.out.write(template.render(path, template_values))
    
class SignIn(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    self.redirect(users.create_login_url('/'))

def main():
  application = webapp.WSGIApplication(
  [
    ('/', MainPage),
    ('/a/create', CreateQuote)
  ], debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()