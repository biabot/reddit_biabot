This is just a reddit bot for biathlon results, code is a bit dirty so dont mind me !

There is a config file needed for this bot, you need a .env file with your login credential, format is like that : 

```shell
REDDIT_CLIENT_ID="XXXXXXX"
REDDIT_CLIENT_SECRET="XXXXXXX"
REDDIT_USER_AGENT="XXXXXXX"
REDDIT_USERNAME="XXXXXXX"
REDDIT_PASSWORD="XXXXXXX"
SOURCE_URL="https://www.realbiathlon.com/mdbConnection.php"
```

There is a sample Json file with the information I used, this was a single relay, so it may change depending on the race type, feel free to use it !

I try to keep the source of the data secret so they dont change, if you care I can tell you in message