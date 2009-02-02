
var tweetlist = {}

function addTweet(){
    $('add-tweet-button').set('disabled','disabled')
    $('add-tweet-button').set('value','…')
    var statusId = $('status-id-field').get('value').replace(/(http:\/\/twitter.com\/.*\/status\/)?([^\/|\?|#]*).*/ig,'$2')
    var url = '/a/loadtweet'
    var jsonRequest = new Request.JSON({'url': url, onComplete: onTweetLoaded}).get({'id': statusId, 'fmt': 'json'});
    return false
}

function onTweetLoaded(response){
    $('add-tweet-button').set('value','+')
    $('add-tweet-button').erase('disabled')
    $('status-id-field').set('value','')
    console.log(response)
    if(!tweetlist[response.id]){
        tweetlist[response.id] = response;
        addTweetToPreview(response)
    }else{
        console(tweetlist)
    }
}

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
        '7200000' : 'one hour ago',
        '86400000' : '{h} hours ago',
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

function linkify(s) {
    var re = /(http:\/\/|ftp:\/\/|https:\/\/|www\.|ftp\.[\w]+)([\w\-\.,@?^=%&amp;:\/~\+#]*[\w\-\@?^=%&amp;\/~\+#])/gi;
    var result = s.replace(re, '<a href="$1$2" >$1$2</a>');
    return result;
}

function twitter_at_linkify(s){
    var re = /(@)([\w]+)/gi;
    var result = s.replace(re, '<a href="http://twitter.com/$2" >$1$2</a>');
    return result;
}

function addTweetToPreview(tweet){
    console.log('addTweetToPreview')
    var tweet_time = Date.parse(tweet.created_at)
    var isotime = ISOTime(tweet_time)
    var humantime= elapsedTime(tweet_time)
    var twitter_app=''
    var newTweet = new Element('li',{
        'id' : 'status_'+tweet.id,
        'class' : 'hentry status u-'+tweet.user.screen_name,
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
    html += '            <span title="'+isotime+'" class="published">'+humantime+'</span></a> <span>from '+twitter_app+'</span>'
    html += '        </span>'
    html += '    </div>'
    newTweet.innerHTML = html
    var quote_tweets = $$('li')
    if(quote_tweets.length == 0){
        var container = $('quote')
        newTweet.inject(container)
    } else {
        for(var i=0; i< quote_tweets.length; i++){
            if (quote_tweets[i].get('_time') > newTweet.get('_time')){
                newTweet.inject(quote_tweets[i],'before')
                break
            }
            if (i == quote_tweets.length-1){
                newTweet.inject(quote_tweets[i],'after')
            }
        }
    }
    
}
function createQuote(){
    return false
}