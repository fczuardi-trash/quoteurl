#
# QuoteURL - URL for Twitter Dialogues
#
# Copyright (c) 2009, Fabricio Zuardi
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
__license__ = "BSD"

import os
import re
import cgi
import wsgiref.handlers
import urllib
import sets

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from django.utils import simplejson
from datetime import datetime
from random import randrange



#--- CONSTANTS ---
MAX_QUOTE_SIZE_SIGNED_OUT = 4
MAX_QUOTE_SIZE_SIGNED_IN  = 10
LOADED_TWEET_CACHE_TIME   = 60*60 # one hour
URL_HASH_SIZE             = 5

#--- MODELS ---
class TwitterUser(db.Model):
  description             = db.StringProperty()
  followers_count         = db.IntegerProperty()
  user_id                 = db.StringProperty()
  numeric_user_id         = db.IntegerProperty()
  location                = db.StringProperty()
  name                    = db.StringProperty()
  profile_image_url       = db.LinkProperty()
  protected               = db.BooleanProperty()
  screen_name             = db.StringProperty()
  url                     = db.LinkProperty()
  updated_date            = db.DateTimeProperty(auto_now=True)
  imported_date           = db.DateTimeProperty(auto_now_add=True)
  json                    = db.TextProperty()
  citations               = db.IntegerProperty(default=0)                # not real time
  latest_citations_update = db.DateTimeProperty()

class Tweet(db.Model):
  tweet_id                      = db.StringProperty()
  numeric_tweet_id              = db.IntegerProperty()
  created_at                    = db.DateTimeProperty()
  favorited                     = db.BooleanProperty()
  in_reply_to_screen_name       = db.StringProperty()
  in_reply_to_status_id         = db.StringProperty()
  numeric_in_reply_to_status_id = db.IntegerProperty()
  in_reply_to_user_id           = db.StringProperty()
  source                        = db.StringProperty()
  text                          = db.StringProperty()
  truncated                     = db.BooleanProperty()
  author_screen_name            = db.StringProperty()
  author_id                     = db.StringProperty()
  author                        = db.ReferenceProperty(TwitterUser)
  updated_date                  = db.DateTimeProperty(auto_now=True)
  imported_date                 = db.DateTimeProperty(auto_now_add=True)
  json                          = db.TextProperty()
  citations                     = db.IntegerProperty(default=0)  # not real time
  latest_citations_update       = db.DateTimeProperty()

class GitHubUser(db.Model):
  screen_name       = db.StringProperty()
  updated_date      = db.DateTimeProperty(auto_now=True)
  imported_date     = db.DateTimeProperty(auto_now_add=True)
  

class QuoteURLUser(db.Model):
  name                  = db.StringProperty()
  description           = db.StringProperty()
  screen_name           = db.StringProperty()
  profile_image_url     = db.LinkProperty()
  url                   = db.LinkProperty()
  twitter_screen_name   = db.LinkProperty()
  github_screen_name    = db.LinkProperty()
  email                 = db.EmailProperty()
  secondary_emails      = db.ListProperty(unicode)
  location              = db.StringProperty()
  geo_point             = db.GeoPtProperty()
  quotes_created        = db.IntegerProperty(default=0)
  birthday              = db.DateTimeProperty()
  created_date          = db.DateTimeProperty(auto_now_add=True)
  updated_date          = db.DateTimeProperty(auto_now=True)
  membership_type       = db.StringProperty()
  google_user           = db.UserProperty()
  twitter_user          = db.ReferenceProperty(TwitterUser) #requires claim
  github_user           = db.ReferenceProperty(GitHubUser)  #requires claim
  rating                = db.RatingProperty()                  # not real time
  latest_rating_update  = db.DateTimeProperty()

class Dialogue(db.Model):
  title                 = db.StringProperty()
  short                 = db.StringProperty()
  alias                 = db.StringProperty()
  tweet_id_list         = db.StringListProperty()
  authors               = db.StringProperty()
  author_list           = db.StringListProperty()
  author_id_list        = db.StringListProperty()
  quoted_by             = db.UserProperty()
  quoter_ip             = db.StringProperty()
  quoter_user_agent     = db.StringProperty()
  tags                  = db.ListProperty(db.Category)
  created_date          = db.DateTimeProperty(auto_now_add=True)
  updated_date          = db.DateTimeProperty(auto_now=True)
  json                  = db.TextProperty()
  rating                = db.RatingProperty()  # not real time
  latest_rating_update  = db.DateTimeProperty()


#--- HELPERS ---
def updateTwitterUserAttributes(user, dictionary):
  # if the user entity already exists update it, otherwise create a new entity
  user.description        = dictionary['description']
  user.location           = dictionary['location']
  user.name               = dictionary['name']
  user.profile_image_url  = dictionary['profile_image_url']
  user.screen_name        = dictionary['screen_name']
  user.url                = dictionary['url']
  user.protected          = bool(dictionary['protected'])
  user.followers_count    = int(dictionary['followers_count'])
  user.user_id            = str(dictionary['id'])
  user.numeric_user_id    = int(dictionary['id'])
  user.json               = simplejson.dumps(dictionary)
  return user

def updateTweetAttributes(tweet, dictionary):
  tweet.created_at              = datetime.strptime(dictionary['created_at'], "%a %b %d %H:%M:%S +0000 %Y")
  tweet.in_reply_to_screen_name = dictionary['in_reply_to_screen_name']
  tweet.source                  = dictionary['source']
  tweet.text                    = dictionary['text']
  tweet.author_screen_name      = dictionary['user']['screen_name']
  tweet.tweet_id                = str(dictionary['id'])
  tweet.numeric_tweet_id        = int(dictionary['id'])
  tweet.favorited               = bool(dictionary['favorited'])
  tweet.in_reply_to_status_id   = str(dictionary['in_reply_to_status_id'])
  tweet.truncated               = bool(dictionary['truncated'])
  tweet.author_id               = str(dictionary['user']['id'])
  tweet.in_reply_to_user_id     = str(dictionary['in_reply_to_user_id'])
  tweet.json                    = simplejson.dumps(dictionary)
  if dictionary['in_reply_to_status_id'] is not None:
    tweet.numeric_in_reply_to_status_id = int(dictionary['in_reply_to_status_id'])

def randomHash(size):
  c = "abcdefghijklmnopqrstuvxywz0123456789"
  l, h = len(c) , ''
  while len(h) < size: h += c[randrange(0,l)]
  return h

#--- ENTRYPOINTS ---

class MainPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      msg_help1 = 'Anonymous users can add up to <em id="quote-size-limit">'+str(MAX_QUOTE_SIZE_SIGNED_OUT)+'</em> Tweets per quote, <a href="/a/login">Sign-in</a> if you need more'
    else:
      msg_help1 = 'You can add up to <em id="quote-size-limit">'+str(MAX_QUOTE_SIZE_SIGNED_IN)+'</em> Tweets per quote. If you need more visit the <a href="/a/upgrade">upgrade membership</a> page.'
    
    template_values = {
      'msg_help1' : msg_help1
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
    self.response.out.write(template.render(path, template_values))

class LoadTweet(webapp.RequestHandler):
  def get(self):
    tweet_id    = cgi.escape(self.request.get('id'))
    fmt         = cgi.escape(self.request.get('fmt'))
    url         = 'http://twitter.com/statuses/show/'+ tweet_id +'.json'
    key         = 'tweet_'+ tweet_id +'.json'
    tweet_json  = memcache.get(key)
    if tweet_json is not None:
      self.response.out.write(tweet_json)
      return True
    else:
      result = urlfetch.fetch(url)
      if result.status_code == 200:
        self.response.out.write(result.content)
        memcache.add(key, result.content, LOADED_TWEET_CACHE_TIME)
        return True
      else:
        self.response.set_status(result.status_code)
        self.response.out.write(result.content)
        return False

class CreateQuote(webapp.RequestHandler):
    
  def post(self):
    status_list     = cgi.escape(self.request.get('statuses')).replace(',',' ').split()
    author_list     = cgi.escape(self.request.get('authors')).replace(',',' ').split()
    author_id_list  = cgi.escape(self.request.get('author_ids')).replace(',',' ').split()
    json            = cgi.escape(self.request.get('json'))
    user            = users.get_current_user()
    ip              = os.environ['REMOTE_ADDR']
    ua              = os.environ['HTTP_USER_AGENT']
    tweets_to_put   = []
    users_to_put    = []
    tweets          = []
    remaining_authors = list(sets.Set(author_id_list[:]))
    
    # logged user or anonymous?
    if not user:
      quote_limit = MAX_QUOTE_SIZE_SIGNED_OUT
      quoteURL_user = None
      dialogue_parent = None
      dialogue_user_email = 'ANONYMOUS'
    else:
      quote_limit = MAX_QUOTE_SIZE_SIGNED_IN
      quoteURL_user = QuoteURLUser.get_or_insert(key_name='QuoteURLUser:'+user.email(),
                                                  email = user.email(),
                                                  google_user = user
                                                )
      dialogue_parent = quoteURL_user
      dialogue_user_email = user.email()
      

    #check to see if the user is trying to manually cheat her limits
    if (len(status_list) > quote_limit):
      path = os.path.join(os.path.dirname(__file__), 'templates/error_limit_exceeded.html')
      self.response.set_status(400)
      self.response.out.write(template.render(path, {'login_url' : '/a/login'}))
      return False

    # iterate through all quoted tweets and see if it's cached or exists in the DataStore, if not load their contents from Twitter
    for tweet_id in status_list:
      cache_key = 'tweet_'+ tweet_id +'.json'
      tweet_json = memcache.get(cache_key)
      if tweet_json is None:
        # json not on cache, load from twitter again
        #@TODO
        self.response.out.write('Zuardi needs to implement the re-fetch from Twitter after cache timeout. Blame him! :)')
        return False
      else:
        # json is on the cache, good
        pass
      
      # load json info into a python object
      loaded_tweet = simplejson.loads(tweet_json)
      
      # create/update tweet
      tweet = Tweet.get_or_insert(key_name='Tweet:'+str(loaded_tweet['id']))
      updateTweetAttributes(tweet, loaded_tweet)
      tweets_to_put.append(tweet)
      tweets.append(loaded_tweet)
      
      # check if the user has been included already in the "list of users to put"
      if  tweet.author_id in remaining_authors:
        #create/update twitter user
        twitter_user = TwitterUser.get_or_insert(key_name='TwitterUser:'+tweet.author_id)
        updateTwitterUserAttributes(twitter_user, loaded_tweet['user'])
        users_to_put.append(twitter_user)
        remaining_authors.remove(tweet.author_id)
      else:
        pass
    
    # put all users in the DataStore, updating the existing ones
    user_keys = db.put(users_to_put);
    
    # update the information on the tweets to include author datastore references
    for tweet in tweets_to_put:
      tweet.author = TwitterUser.get_by_key_name('TwitterUser:'+tweet.author_id).key()
    # put all tweets in the DataStore, updating the existing ones
    tweet_keys = db.put(tweets_to_put);
    
    dialogue_title = ' '.join(status_list)
    
    dialogue = Dialogue.get_or_insert(
                                    parent=dialogue_parent,
                                    key_name='Dialogue:'+dialogue_user_email+':'+dialogue_title
                                    )
    dialogue.title = dialogue_title
    dialogue.tweet_id_list = status_list
    dialogue.quoted_by = user
    dialogue.quoter_ip = ip
    dialogue.quoter_user_agent = ua
    dialogue.alias = None
    dialogue.authors = ' '.join(author_list)
    dialogue.author_list = author_list
    dialogue.author_id_list = author_id_list
    dialogue.rating = None
    dialogue.tags = []
    dialogue.json = json
    if not dialogue.short:
      h = randomHash(URL_HASH_SIZE)
      while Dialogue.gql("WHERE short = :1", h).get() is not None :
        h = randomHash(URL_HASH_SIZE)
      dialogue.short = h

    # a transaction that: 
    # 1- increments the quotes_created counter for the quoteURLUser
    # 2- save quoteURLUser and the created dialogue entity
    def save_dialogue():
      quoteURL_user.quotes_created += 1
      db.put([quoteURL_user, dialogue])
    
    if not user:
      # quotes created anonymously can be saved direct
      dialogue.put()
    else:
      db.run_in_transaction(save_dialogue)
    
    # display success page
    template_values = {
      'short'     : dialogue.short,
      'app_url'   : os.environ['HTTP_HOST'],
      'tweets'    : tweets
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/show.html')
    self.response.out.write(template.render(path, template_values))
    return True

class ShowQuote(webapp.RequestHandler):
  def get(self, short, rubish):
    if rubish:
      self.redirect('/'+short)
      return False
    dialogue = Dialogue.gql("WHERE short = :1", short).get()
    if not dialogue:
      path = os.path.join(os.path.dirname(__file__), 'templates/error_quote_not_found.html')
      self.response.set_status(404)
      self.response.out.write(template.render(path, {}))
      return False
    tweets = simplejson.loads(dialogue.json)
    template_values = {
      'tweets'    : tweets
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/show.html')
    self.response.out.write(template.render(path, template_values))
    return True
    

class Test(webapp.RequestHandler):
  def get(self):
    c = "abcdefghijklmnopqrstuvxywz0123456789"
    l, key = len(c) , ''
    while len(key) < 5: key += c[randrange(0,l)]
    self.response.out.write(key)
    
class SignIn(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    self.redirect(users.create_login_url('/'))
    
class UpgradeMembership(webapp.RequestHandler):
  def get(self):
    template_values = {}
    path = os.path.join(os.path.dirname(__file__), 'templates/upgrade.html')
    self.response.out.write(template.render(path, template_values))


#--- MAPPINGS ---
def main():
  application = webapp.WSGIApplication(
  [
    ('/'                  , MainPage),
    ('/a/login'           , SignIn),
    ('/a/upgrade'         , UpgradeMembership),
    ('/a/loadtweet'       , LoadTweet),
    ('/a/create'          , CreateQuote),
    ('/(.[a-z0-9]+)(.*)'  , ShowQuote)
  ], debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()