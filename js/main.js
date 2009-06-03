/**
 * QuoteURL - URL for Twitter Dialogues
 *
 * Copyright (c) 2009, Fabricio Zuardi
 * All rights reserved.
 *  
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 
 *   * Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *   * Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in
 *     the documentation and/or other materials provided with the
 *     distribution.
 *   * Neither the name of the author nor the names of its contributors
 *     may be used to endorse or promote products derived from this
 *     software without specific prior written permission.
 *  
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 **/

//container for the tweets that will make a quote
var tweetlist = {}

//interval to be used when user turns autoadd on
var auto_add_interval = 0

//interval to be used to check when the user closed the popup
var check_popup_state_interval = 0

// global preferences
var preferences = {
    'order' : 'asc'
}
var embed_styles = null
var popup_window

//For people without firebug
if (!console) {
  var console = {}
  console.log = function(text){
    return
  }
}

/** Load the contents of the tweet to be added to the preview panel **/
function loadTweet(){
    //extract id from the input
    var statusId = $('status-id-field').get('value').replace(/(http:\/\/.*\.?twitter.com\/.*\/status(es)?\/)?([^\/|\?|#|\s]*).*/ig,'$3')
    //warn the user if her limit exceeded
    if ($$('li').length >= parseInt($('quote-size-limit').get('text'))+1) return limitExceeded()
    //warn the user if the tweet is already listed
    if (tweetlist[statusId] != undefined) return dupeTweet()
    //disable add button
    $('add-tweet-button').set('disabled',true)
    $('add-tweet-button').set('value','…')
    //request tweet
    var url = '/a/loadtweet'
    var jsonRequest = new Request.JSON({'url': url, onComplete: requestComplete, onSuccess: onTweetLoaded, onFailure: onTweetLoadFailure}).post({'id': statusId, 'fmt': 'json'});
    return false
}

/** Callback function when the request completes, regardless of if it succeded or failed **/
function requestComplete(response){
    console.log('requestComplete')
    console.log(response)
    //re-enable add button and clean the text input
    $('add-tweet-button').set('value','+')
    $('add-tweet-button').erase('disabled')
    $('status-id-field').set('value','')
    return false
}

/** Callback function to run if the tweet content is returned **/
function onTweetLoaded(response){
    console.log('onTweetLoaded')
    //add the loaded tweet to the quote
    tweetlist[response.id] = response;
    addTweetToPreview(response)
}

/** Modify the page to include the loaded tweet in the preview panel **/
function addTweetToPreview(tweet){
    var tweet_time = Date.parse(tweet.created_at)
    var isotime = ISOTime(tweet_time)
    var humantime = elapsedTime(tweet_time)
    var in_reply_to = (tweet.in_reply_to_status_id != null && tweet.in_reply_to_screen_name != null) ? 
    ' <a href="http://twitter.com/'+tweet.in_reply_to_screen_name+'/status/'+tweet.in_reply_to_status_id+'">in reply to '+tweet.in_reply_to_screen_name+'</a>' : ''
    var newTweet = new Element('li',{
        'id' : 'status_'+tweet.id,
        'class' : 'hentry status u-'+tweet.user.screen_name,
        'style' : 'left:-100%',
        '_time' : tweet_time})
    var html = ''
    html += '    <div class="thumb vcard author">'
    html += '        <a class="url" href="http://twitter.com/'+tweet.user.screen_name+'">'
    html += '            <img width="48" height="48" src="'+tweet.user.profile_image_url+'" class="photo fn" alt="'+tweet.user.name+'"/>'
    html += '        </a>'
    html += '    </div>'
    html += '    <div class="status-body">'
    html += '        <a class="author" title="'+tweet.user.name+'" href="http://twitter.com/'+tweet.user.screen_name+'">'+tweet.user.screen_name+'</a>'
    html += '        <span class="entry-content">'
    html += '            '+twitter_at_linkify(linkify(tweet.text))
    html += '        </span>'
    html += '        <span class="meta entry-meta">'
    html += '            <a rel="bookmark" class="entry-date" href="http://twitter.com/'+tweet.user.screen_name+'/status/'+tweet.id+'">'
    html += '            <span title="'+isotime+'" class="published">'+humantime+'</span></a> <span>from '+tweet.source+'</span>'+in_reply_to
    html += '        </span>'
    html += '    </div>'
    html += '    <div class="actions">'
    html += '        <a class="del" href="#" id="del_'+tweet.id+'" onclick="return removeTweet(this);">x</a>'
    html += '    </div>'
    newTweet.set('html', html)
    //existing tweets in the quote preview
    var quote_tweets = $$('li')
    if(quote_tweets.length == 1){
        quote_tweets[0].style.display = 'none'
        var container = $('quote')
        newTweet.inject(container)
    } else {
        for(var i=0; i< quote_tweets.length; i++){
            if (tweetComesBefore(newTweet, quote_tweets[i])){
                newTweet.inject(quote_tweets[i],'before')
                quote_tweets[i].style.top = '-'+newTweet.offsetHeight+'px'
                quote_tweets[i].set('tween', {duration: 'short'})
                quote_tweets[i].tween('top', '0px')
                break
            }
            //last position
            if (i == quote_tweets.length-1){
                newTweet.inject(quote_tweets[i],'after')
            }
        }
    }
    updateForm()
    newTweet.set('tween', {duration: 'long'});
    newTweet.tween('left', '0%');
}

function updateForm(){
    var statuses = []
    var authors = []
    var author_ids = []
    var tweet_id = ''
    var tweets = $$('li')
    for (var i=1; i<tweets.length; i++){
        tweet_id = tweets[i].id.substring('status_'.length, tweets[i].id.length)
        statuses.push(tweet_id)
        authors.push(tweetlist[tweet_id].user.screen_name)
        author_ids.push(tweetlist[tweet_id].user.id)
    }
    $('form-statuses').set('value', statuses.join(' '))
    $('form-authors').set('value', authors.join(' '))
    console.log('updateForm')
    console.log( author_ids.join(' '))
    $('form-author-ids').set('value', author_ids.join(' '))
    updateSaveButton()
}

function updateSaveButton(){
    var quote_tweets = $$('li')
    if (quote_tweets.length < 3){
        $('save-button').set('disabled', true)
        $('save-button').addClass('disabled')
    } else {
        $('save-button').set('disabled', false)
        $('save-button').removeClass('disabled')
    }
    updateIframeHeight()
}

function updateIframeHeight(){
    $('twitter-container').style.height = ($('main-container').offsetHeight-33)+'px'
}

/** Compare 2 tweets and return true if tweet a comes before b in the current ordering (timestamp-based) **/
function tweetComesBefore(a,b){
    if (preferences.order == 'asc') {
        return (a.get('_time') < b.get('_time'))
    } else {
        return (a.get('_time') > b.get('_time'))
    }
}

/** Remove the Tweet from the preview panel and from the list **/
function removeTweet(del_button){
    var tweet_id = del_button.id.substring('del_'.length, del_button.id.length)
    delete tweetlist[tweet_id]
    $('status_'+tweet_id).dispose()
    updateForm()
    return false
}

/** Validate and sends necessary data to create the new quote page **/
function createQuote(){
    closePopupMode()
    return true
}

function launchPopupMode(link){
    var quoteurl_half = $('main-container')
    var twitter_half = $('twitter-container')
    quoteurl_half.style.width = '50%'
    twitter_half.style.width = '45%'
    twitter_half.style.visibility = 'visible'
    document.body.addClass('splitted')
    var popScreenX = window.screenX + twitter_half.offsetLeft
    var popScreenY = window.screenY
    var popWidth = twitter_half.offsetWidth + 20
    var popHeight = window.innerHeight + 20
    popup_window = window.open(link.get('href'),link.get('_windowname'),
    'scrollbars=yes,screenX='+popScreenX+',screenY='+popScreenY+',width='+popWidth+',height='+popHeight);
    popup_window.focus()
    check_popup_state_interval = setInterval(function(){
        try{
            if (popup_window.closed === true){
                closePopupMode()
            }
            updateIframeHeight()
        }catch(e){
            console.log(e)
        }
    },500)
    return false
}

function closePopupMode(){
    var quoteurl_half = $('main-container')
    var twitter_half = $('twitter-container')
    quoteurl_half.style.width = '98%'
    twitter_half.style.width = '1%'
    twitter_half.style.visibility = 'hidden'
    document.body.removeClass('splitted')
    clearInterval(check_popup_state_interval)
    popup_window.close()
}

function enableAutoAdd(){
    $('status-id-field').set('_last_value', $('status-id-field').value)
    auto_add_interval = setInterval(function(){
        if(($('status-id-field').get('_last_value') == undefined) && ($('status-id-field').get('value').length > 5)){
            loadTweet()
        }
        $('status-id-field').set('_last_value', $('status-id-field').value)
    },300)
}

function toggleEmbedStyle(check){
    var styled = check.get('checked')
    var embed_field = $('quoteURL-embed-field')
    if (embed_styles == null){
        //first-time, store the style info
        embed_styles = embed_field.value.match(/<.*?style="[^"]*"/g)
    }
    var lastindex = 0;
    var embed_string = embed_field.value
    if (!styled) {
        //remove style
        for (var i=0; i<embed_styles.length; i++){
            lastindex = embed_string.indexOf(embed_styles[i],lastindex)
            embed_string =  embed_string.substring(0,lastindex) +
                                embed_styles[i].substring(0, embed_styles[i].indexOf('style="')-1) +
                                embed_string.substring(lastindex+embed_styles[i].length, embed_string.length)
        }
        embed_field.value = embed_string.replace('QuoteURL styled embed start','QuoteURL no-style embed start')
    } else {
        //put styles back
        for (var i=0; i<embed_styles.length; i++){
            var searchfor = embed_styles[i].substring(0, embed_styles[i].indexOf('style="')-1)
            lastindex = embed_string.indexOf(searchfor,lastindex)
            embed_string =  embed_string.substring(0,lastindex) +
                                embed_styles[i] +
                                embed_string.substring(lastindex+searchfor.length, embed_string.length)
        }
        embed_field.value = embed_string.replace('QuoteURL no-style embed start','QuoteURL styled embed start')
    }
}
//--- Errors and Warnings ---

/** 
* Displays a message to the user
* @param    msg     String - the message
* @param    mode    String - the classname to use on the warning ('FAIL','WIN')
* @param    delay   Number - the time in miliseconds the message will stay on screen
**/
function warnUser(msg, mode, delay){
    if (delay==undefined) delay = 2300;
    var feedbackdiv = $('feedback')
    var color = (mode=='FAIL') ? '#c33' : '#3c3'
    var background_color = (mode=='FAIL') ? '#fee' : '#efe'
    feedbackdiv.className = mode
    feedbackdiv.style.backgroundColor = color
    $('feedback-message').set('text', msg)
    feedbackdiv.fade('show')
    feedbackdiv.tween('background-color', background_color)
    setTimeout(function(){$('feedback').fade('out')}, delay)
    return false
}

/** The user has tried to add more tweets than it is allowed to **/
function limitExceeded(){
    warnUser('FAIL: You have reached your quote size limit, try removing some by clicking the "x" buttons.','FAIL',4000)
    return false
}

/** The user has tried to add a tweet that is already on the preview list **/
function dupeTweet(){
    warnUser('Hooray! This tweet is already on your list.','WIN',3000);
    return requestComplete()
}

/** Callback function to run if there was an error loading the tweet **/
function onTweetLoadFailure(r){
    console.log('TweetLoadFailure')
    console.log(r)
    warnUser('FAIL: '+r.status+' - '+JSON.decode(r.responseText).error,'FAIL')
}


//--- Utilities ---

function selectField(f){
    f.focus();
    f.select();
    return true
}

/** Complete date plus hours, minutes and seconds as specified in ISO 8601 **/
function ISOTime(time){
    var date = new Date();
    date.setTime(time)
    var year = date.getUTCFullYear()
    var month = date.getUTCMonth()+1
    var day = date.getUTCDate()
    var hours = date.getUTCHours()
    var minutes = date.getUTCMinutes()
    var seconds = date.getUTCSeconds()
    var items = [month, day, hours, minutes, seconds]
    items.each( function(item){ if (item < 10) item = '0' + item });
    return year+'-'+month+'-'+day+'T'+hours+':'+minutes+':'+seconds+'+00:00'
}

/** Human-friendly elapsed time messages **/
function elapsedTime(time){
    var date = new Date();
    date.setTime(time)
    var delta = $time() - time
    var intervals = {
        '1000' : 'just now',
        '30000' : '{s} seconds ago',
        '60000' : 'less than a minute ago',
        '120000' : 'one minute ago',
        '3600000' : '{m} minutes ago',
        '7200000' : 'about one hour ago',
        '86400000' : 'about {h} hours ago',
        '172800000' : 'yesterday',
        '2592000000' : '{d} days ago'
    }
    for (var i in intervals){
        var replacements = {
                's' : Math.floor(delta/1000),
                'm' : Math.floor(delta/1000/60),
                'h' : Math.floor(delta/1000/60/60),
                'd' : Math.floor(delta/1000/60/60/24)
            };
        if (delta < i){
            return intervals[i].substitute(replacements)
        }
    }
    return (date.getMonth()+1)+'/'+date.getDate()+
    ((date.getFullYear() == new Date().getFullYear()) ? '' : ('/'+date.getFullYear()))+ 
    (' - '+date.getHours()+':'+date.getMinutes());
}

/** turn text web urls into html a links **/
function linkify(s) {
    var re = /(http:\/\/|ftp:\/\/|https:\/\/|www\.|ftp\.[\w]+)([\w\-\.,@?^=%&amp;:\/~\+#]*[\w\-\@?^=%&amp;\/~\+#])/gi;
    var result = s.replace(re, '<a href="$1$2" >$1$2</a>');
    return result;
}

/** turn @nicknames into html links for the twitter page for that user **/
function twitter_at_linkify(s){
    var re = /(@)([\w]+)/gi;
    var result = s.replace(re, '<a href="http://twitter.com/$2" >$1$2</a>');
    return result;
}