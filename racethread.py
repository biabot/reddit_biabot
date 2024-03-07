import praw
import requests
import os
import json
from datetime import timezone
import pytz
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re
import time
from bs4 import BeautifulSoup
from unidecode import unidecode



def main():
    print("start race thread at : " + str(time.time()))
    load_dotenv()
    reddit = praw.Reddit(client_id=os.environ['REDDIT_CLIENT_ID'],
                         client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                         user_agent=os.environ['REDDIT_USER_AGENT'],
                         username=os.environ['REDDIT_USERNAME'],
                         password=os.environ['REDDIT_PASSWORD'])


    sys.stdout.flush()
    response = requests.get( os.environ['SOURCE_RACE_URL'])
    response.raise_for_status()
    jsonResponse = response.json()

    blueBib = getBlueBib()
    for rez in jsonResponse["athletesList"]:
        # is in GMT
        raceTime = datetime.utcfromtimestamp(rez['epoch']).strftime('%d/%m/%Y')
        nowTime = (datetime.now(timezone.utc) - timedelta(days=0)).strftime('%d/%m/%Y')

        if rez['eventClass'] in ['BTSWRLCP', 'BTSWRLCH']:
            if raceTime == nowTime:
                rez['eventDescription'] = rez['eventDescription'].replace('BMW ', '').replace('IBU ', '').replace(' Biathlon', '')
                title = "Race Thread: "+ rez['eventDescription'] +" "+ jsonResponse['seasonId'][:2] + "/"+ jsonResponse['seasonId'][2:] + " "+rez['eventOrganizer']+" - "+rez['shortDescription']+""
                title = re.sub(' [1-9x]+(\.)?([0-9]) km', '', title)
                body = makeRaceThread(rez)
                body += getRanking(rez, os.environ['SOURCE_URL'], blueBib)
                # reddit.subreddit('biathlon').submit(title, body, "", "92defafc-b47c-11e6-a893-0e403872dda2", "Race Thread")
                reddit.validate_on_submit = 1
                # reddit.subreddit('testingground4bots').submit(title, body, "", "7c7255be-02b3-11eb-95d1-0e921f8587e3", "Meta")
                print("posted "+ title)
                # print(body)
                return

    print("end race thread at : " + str(time.time()))


def makeRaceThread(raceInfo):
    my_datetime_cet = datetime.fromtimestamp(raceInfo['epoch']).astimezone(pytz.timezone('Europe/Berlin')).strftime('%-H:%M')

    text = ("Starting time: "+my_datetime_cet+" CET\n\n"
            "Start list [here](https://www.biathlonworld.com/startlist/" + raceInfo["raceId"] + ")\n\n"
            "Datacenter: [here](https://www.biathlonresults.com/#/datacenter)\n\n"
            "New site here: [https://eurovisionsport.com/](https://eurovisionsport.com/) You have to make an account.\n\n"
            "I assume this is still valid: **This stream is unavailable in** [**France**](https://www.lequipe.fr/)**,** [**Denmark**](https://play.tv2.dk/) **and** [**Norway**](https://www.tv2.no/sport/)**.**\n\n"
            )

    return text

def getRanking(raceInfo, url, blueBib):
    race_type_four = raceInfo['raceId'][-4:]
    race_type_two = raceInfo['raceId'][-2:]
    if race_type_four in ['MXSR', 'MXRL']:
        category = "Team"
        race_type_two="MX"
    elif race_type_two in ['RL']:
        category = "Team"
        race_type_two="RL"
    else:
        category = "Individual"
        race_type_two=race_type_two

    form_data = {'operation': "query",
                 'filter': '{"year":' + str(raceInfo["year"]) + ', "category":"'+category+'","gender":"'+raceInfo['gender']+'","discipline":"'+str(race_type_two)+'"}',
                 'options': '{"limit":1}',
                 'projection': '{}',
                 'namespace': 'Analysis.SeasonScores'}

    server = requests.post(url, data=form_data)
    ranking = json.loads(server.text)[0]
    womenBlueBib = blueBib[0]
    menBlueBib = blueBib[1]

    text = "Current top 10 "+ re.sub(' [1-9]+(\.)?([0-9]) km', '', raceInfo['shortDescription']) +" Cup rankings:\n\n"

    if category == "Team":
        text += "|#|Nation|Points|\n"
        text += "|:-|:-|:-|\n"
    else:
        text += "|#|Athlete|Nation|Points|\n"
        text += "|:-|:-|:-|:-|\n"

    for rez in ranking['scores']:
        if rez['rank'] <= 10:
            rankDif = rez["rankDiff"]
            if str(rankDif) == "None":
                rankDif = 0
            if rankDif*-1 > 0:
                rankDif = "+" + str(rankDif*-1)
            else:
                rankDif = str(rankDif*-1)

            if rez['rank'] == 1:
                bib = "🔴"
            elif rez["givenName"].lower() == womenBlueBib.lower():
                bib = "🔵"
            elif rez["givenName"].lower() == menBlueBib.lower():
                bib = "🔵"
            else:
                bib = ""
            if category == "Team":
                text += "|"+str(rez['rank'])+"|"+rez["country"]+"|"+str(rez['score'])+"|\n"
            else:
                text += "|"+str(rez['rank'])+" ("+ rankDif +")|"+rez["givenName"]+ " "+ rez["familyName"] + " " +bib+"|"+rez["nation"]+"|"+str(rez['score'])+"|\n"


    if category != "Team":
        return getOverallRanking(raceInfo, url, blueBib) + text
    else:
        return text


def getOverallRanking(raceInfo, url, blueBib):

    text = "Current top 10 World Cup rankings:\n\n"
    form_data = {'operation': "query",
                 'filter': '{"year":' + str(raceInfo["year"]) + ', "category":"Individual","gender":"' + raceInfo[
                     'gender'] + '","discipline":"NonTeam"}',
                 'options': '{"limit":1}',
                 'projection': '{}',
                 'namespace': 'Analysis.SeasonScores'}

    server = requests.post(url, data=form_data)
    ranking = json.loads(server.text)[0]

    text += "|#|Athlete|Nation|Points|\n"
    text += "|:-|:-|:-|:-|\n"
    womenBlueBib = blueBib[0]
    menBlueBib = blueBib[1]
    for rez in ranking['scores']:
        if rez['rank'] <= 10:
            rankDif = rez["rankDiff"]
            if str(rankDif) == "None":
                rankDif = 0
            if rankDif*-1 > 0:
                rankDif = "+" + str(rankDif*-1)
            else:
                rankDif = str(rankDif*-1)
            if rez['rank'] == 1:
                bib = "🟡"
            elif rez["givenName"].lower() == womenBlueBib.lower():
                bib = "🔵"
            elif rez["givenName"].lower() == menBlueBib.lower():
                bib = "🔵"
            else:
                bib = ""
            text += "|" + str(rez['rank']) + "("+rankDif+")|" + rez["givenName"] + " " + rez["familyName"] + ""+bib+"|" + rez["nation"] + "|" + str(rez['score']) + "|\n"

    return text

def getBlueBib():
    # get URL
    page = requests.get("https://en.wikipedia.org/wiki/2023%E2%80%9324_Biathlon_World_Cup#Overall_3")

    # scrape webpage
    soup = BeautifulSoup(page.content, 'html.parser')

    # create object
    object = soup.find(id="mw-content-text")

    # find tags
    items = object.find(id="Under_25_4").findParent().find_next('table').find_all('tr')
    result = items[1].find_all('a')[1]
    women_blue_bib = result.text.split(' ')[0]

    # find tags
    items = object.find(id="Under_25_2").findParent().find_next('table').find_all('tr')
    result = items[1].find_all('a')[1]
    men_blue_bib = result.text.split(' ')[0]

    return [unidecode(women_blue_bib), unidecode(men_blue_bib)]


if __name__ == "__main__":
    main()
