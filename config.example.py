'''
Configuration File

'''

'''
The backup_load_tweet_json_url is a URL to get the same result as the
Twitter API 'http://twitter.com/statuses/show/'+ tweet_id +'.json' URL

We do this because many apps on the Google App Engine shares their server IPs
so it is relatively easy to bump on twitter API's usage limits and start 
receiving Error:400 results for the queries.

Since it is not possible to whitelist the AppEngine cloud IPs, this is a
 workaround, you must set on a separated server a page that proxy the
results of the API call for you, and then you can whitelist that particular
 IP if you need.
 
This backup URL must accept one query string GET parameter called 'id'
and return the json for the requested tweeted id.

For example, if you have a host with php support at http://example.com
You can create a loadtweet.php file there containing the following code:

<?php
$tweet_id = $_REQUEST['id'];
$url = 'http://twitter.com/statuses/show/'. $tweet_id .'.json';
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL,$url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER,1);
$content = curl_exec( $ch );
$err     = curl_errno( $ch );
$errmsg  = curl_error( $ch );
$header  = curl_getinfo( $ch );
curl_close( $ch );
$code = $header['http_code'];
if (! $err) {
    header('Content-type: text/plain');
    echo $content;
} else {
    $header_text = 'HTTP/1.0 ' . $code;
    header($header_text);
    echo $errmsg;
}
?>


'''
# backup_load_tweet_json_url ='http://example.com/loadtweet.php'
backup_load_tweet_json_url = None