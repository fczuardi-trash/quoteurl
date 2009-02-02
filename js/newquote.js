
var tweetlist = {}

function addTweet(){
    $('add-tweet-button').set('disabled','disabled')
    $('add-tweet-button').set('value','…')
    var statusId = $('status-id-field').get('value').replace(/(http:\/\/twitter.com\/.*\/status\/)?([^\/|\?|#]*).*/ig,'$2')
    var url = '/a/loadtweet'
    var jsonRequest = new Request.JSON({'url': url, onComplete: onTweetLoaded}).get({'id': statusId, 'fmt': 'json'});
}

function onTweetLoaded(response){
    $('add-tweet-button').set('value','+')
    $('add-tweet-button').erase('disabled')
    console.log(response)
    if(!tweetlist[response.id]){
        tweetlist[response.id] = response;
        addTweetToPreview(response)
    }else{
        console(tweetlist)
    }
}

function addTweetToPreview(tweet){
    console.log('addTweetToPreview')
    //2009-02-02T06:36:54+00:00
    var isotime=''
    var humantime=''
    var twitter_app=''
    var newTweet = new Element('li',{
        'id' : 'status_'+tweet.id,
        'class' : 'hentry status u-'+tweet.user.screen_name,
        '_time' : Date.parse(tweet.created_at)})
    var html = ''
    html += '    <div class="thumb vcard author">'
    html += '        <a class="url" href="http://twitter.com/'+tweet.user.screen_name+'">'
    html += '            <img width="48" height="48" src="'+tweet.user.profile_image_url+'" class="photo fn" alt="'+tweet.user.name+'"/>'
    html += '        </a>'
    html += '    </div>'
    html += '    <div class="status-body">'
    html += '        <a class="author" title="'+tweet.user.name+'" href="http://twitter.com/'+tweet.user.screen_name+'">'+tweet.user.screen_name+'</a>'
    html += '        <span class="entry-content">'
    html += '            '+tweet.text
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
        console.log('inject')
        console.log(newTweet)
        console.log(container)
        newTweet.inject(container)
        console.log(container)
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
    //loop the existing ol
    //compare the timestamp of the existing li with the new, if existin is older, add before
    //if the list ends, append at the end
    console.log('addTweetToPreview end')
}
function createQuote(){
    return false
}