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



#--- CONSTANTS ---
MAX_QUOTE_SIZE_SIGNED_OUT = 4
MAX_QUOTE_SIZE_SIGNED_IN  = 10
LOADED_TWEET_CACHE_TIME   = 60*60 # one hour


#--- MODELS ---
class TwitterUser(db.Model):
  description       = db.StringProperty()
  followers_count   = db.IntegerProperty()
  user_id           = db.StringProperty()
  numeric_user_id   = db.IntegerProperty()
  location          = db.StringProperty()
  name              = db.StringProperty()
  profile_image_url = db.LinkProperty()
  protected         = db.BooleanProperty()
  screen_name       = db.StringProperty()
  url               = db.LinkProperty()
  json              = db.TextProperty()

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
  user                          = db.ReferenceProperty(TwitterUser)
  imported_date                 = db.DateTimeProperty(auto_now_add=True)
  json                          = db.TextProperty()

class Dialogue(db.Model):
  title             = db.StringProperty()
  status_id_list    = db.StringListProperty()
  authors           = db.StringProperty()
  author_list       = db.StringListProperty()
  author_id_list    = db.StringListProperty()
  quoted_by         = db.UserProperty()
  quoter_ip         = db.StringProperty()
  quoter_user_agent = db.StringProperty()
  alias             = db.StringProperty()
  created_date      = db.DateTimeProperty(auto_now_add=True)
  json              = db.TextProperty()


#--- HELPERS ---
class AccessHelper():
  def isProUser(User):
    return False


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

def updateTwitterUserData(user, dictionary):
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

class CreateQuote(webapp.RequestHandler):
    
  def post(self):
    status_list     = cgi.escape(self.request.get('statuses')).replace(',',' ').split()
    author_list     = cgi.escape(self.request.get('authors')).replace(',',' ').split()
    author_id_list  = cgi.escape(self.request.get('author_ids')).replace(',',' ').split()
    json            = cgi.escape(self.request.get('json'))
    user            = users.get_current_user()
    ip              = os.environ['REMOTE_ADDR']
    ua              = os.environ['HTTP_USER_AGENT']
    esisting_users  = {}
    esisting_tweets = {}
    tweets_to_put   = []
    users_to_put    = []
    remaining_authors = list(sets.Set(author_id_list[:]))
    
    #check to see if the user is trying to manually cheat her limits
    if not user:
      quote_limit = MAX_QUOTE_SIZE_SIGNED_OUT
    else:
      quote_limit = MAX_QUOTE_SIZE_SIGNED_IN
    if (len(status_list) > quote_limit):
      path = os.path.join(os.path.dirname(__file__), 'templates/error_limit_exceeded.html')
      self.response.set_status(400)
      self.response.out.write(template.render(path, {'login_url' : '/a/login'}))
      return False

    # query the DataStore to get existing user entities
    user_query = TwitterUser.gql("WHERE user_id IN :user_id_list ", user_id_list=author_id_list)
    for esisting_user in user_query:
      esisting_users[esisting_user.user_id] = esisting_user

    # query the DataStore to get existing tweet entities
    tweet_query = Tweet.gql("WHERE user_id IN :tweet_id_list ", tweet_id_list=status_list)
    for esisting_tweet in tweet_query:
      esisting_tweets[esisting_tweet.tweet_id] = esisting_tweet

    # iterate through all quoted tweets and see if it's cached or exists in the DataStore, if not load their contents from Twitter
    for tweet_id in status_list:
      key = 'tweet_'+ tweet_id +'.json' #cache key
      
      if tweet_id not in esisting_tweets:
        # the tweet entity does not exists in the DataStore and needs to be created
        # try to get the json from cache
        tweet_json = memcache.get(key)
        if tweet_json is None:
          # json not on cache, load from twitter again
          #@TODO
          self.response.out.write('Zuardi needs to implement the re-fetch from Twitter after cache timeout. Blame him! :)')
          return False
        else:
          # json is on the cache, good
          pass
        # a new tweet entity needs to be created based on the loaded json
        new_tweet = Tweet(key_name=str(loaded_tweet['id']))
        loaded_tweet = simplejson.loads(tweet_json)
        new_tweet.tweet_id                = str(loaded_tweet['id'])
        new_tweet.numeric_tweet_id        = int(loaded_tweet['id'])
        new_tweet.created_at              = datetime.strptime(loaded_tweet['created_at'], "%a %b %d %H:%M:%S +0000 %Y")
        new_tweet.favorited               = bool(loaded_tweet['favorited'])
        new_tweet.in_reply_to_screen_name = loaded_tweet['in_reply_to_screen_name']
        new_tweet.in_reply_to_status_id   = str(loaded_tweet['in_reply_to_status_id'])
        new_tweet.in_reply_to_user_id     = loaded_tweet['in_reply_to_user_id']
        new_tweet.source                  = loaded_tweet['source']
        new_tweet.text                    = loaded_tweet['text']
        new_tweet.truncated               = bool(loaded_tweet['truncated'])
        new_tweet.json                    = tweet_json
        new_tweet.author_screen_name      = loaded_tweet['user']['screen_name']
        new_tweet.author_id               = str(loaded_tweet['user']['id'])
        if loaded_tweet['in_reply_to_status_id'] is not None:
          new_tweet.numeric_in_reply_to_status_id = int(loaded_tweet['in_reply_to_status_id'])
        # check if the user has been included already in the "list of users to put"
        if  new_tweet.author_id in remaining_authors:
          # check if the user entity doesnt exists and so needs to be created, or exists and so need to be updated
          if new_tweet.author_id in esisting_users:
            #user entity exists, update
            updateTwitterUserData(esisting_users[new_tweet.author_id], loaded_tweet['user'])
            users_to_put.append(esisting_users[new_tweet.author_id])
          else:
            #user entity does not exist, create
            new_twitter_user = TwitterUser(key_name=new_tweet.author_id)
            updateTwitterUserData(new_twitter_user, loaded_tweet['user'])
            users_to_put.append(new_twitter_user)
          remaining_authors.remove(new_tweet.author_id)
        else:
          pass
        tweets_to_put.append(new_tweet)
      else:
        # the DataStore already contains this tweet, so no need to create the tweet entity
        tweets_to_put.append(esisting_tweets[tweet_id])
        continue
      # end for

    # put all users in the DataStore, updating the existing ones
    user_keys = db.put(users_to_put);
    
    
    # update the information on the tweets to put queue to include user datastore Keys
    for tweet in tweets_to_put:
      
    
    template_values = {
      'tweets_to_put' : tweets_to_put,
      'users_to_put'  : users_to_put,
      'user_keys'     : user_keys
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/test.html')
    self.response.out.write(template.render(path, template_values))
    return True
    
    #  user                         = db.ReferenceProperty(TwitterUser)
    
    dialogue = Dialogue()
    dialogue.title = ' '.join(status_list)
    dialogue.status_id_list = status_list
    dialogue.quoter = user
    dialogue.quoter_ip = ip
    dialogue.quoter_user_agent = ua
    dialogue.alias = None
    dialogue.authors = ' '.join(author_list)
    dialogue.author_list = author_list
    dialogue.author_id_list = author_id_list
    dialogue.json = json
    template_values = {
      'dialogue'    : dialogue,
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/show.html')
    self.response.out.write(template.render(path, template_values))
    return True
    
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
    ('/', MainPage),
    ('/a/login', SignIn),
    ('/a/upgrade', UpgradeMembership),
    ('/a/loadtweet', LoadTweet),
    ('/a/create', CreateQuote)
  ], debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()