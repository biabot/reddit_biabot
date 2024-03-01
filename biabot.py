import praw
import requests
import os
import json
import time
from datetime import timezone
import datetime
from datetime import datetime
import re
import sys
from dotenv import load_dotenv


def main():
    load_dotenv()
    reddit = praw.Reddit(client_id=os.environ['REDDIT_CLIENT_ID'],
                         client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                         user_agent=os.environ['REDDIT_USER_AGENT'],
                         username=os.environ['REDDIT_USERNAME'],
                         password=os.environ['REDDIT_PASSWORD'])

    sys.stdout.flush()
    for comment in reddit.subreddit("biathlon").stream.comments():
        if "!biathlonResult" in comment.body:
            print('found !biathlonResult')
            raceregex = re.compile(r"(BT[A-X0-9_]+)")
            mo1 = raceregex.search(comment.body)
            if mo1.group(1):
                older_than_five = datetime.now(timezone.utc).timestamp() - 500
                if comment.created_utc > older_than_five:
                    print('for race ' + mo1.group(1))
                    # print(report(mo1.group(1), os.environ['SOURCE_URL']))
                    try:
                        comment.reply(report(mo1.group(1), os.environ['SOURCE_URL']))
                        print('output finished for ' + mo1.group(1))
                    except:
                        print("An exception occurred")
                else:
                    print('too old')


def report(raceId, url):
    form_data = {'operation': "query",
                 'filter': '{"raceId":"' + raceId + '"}',
                 'options': '{"limit":1}',
                 'projection': '{}',
                 'namespace': 'Results.Races'}

    server = requests.post(url, data=form_data)
    results = json.loads(server.text)[0]

    race_type = results['raceId'][-2:]
    top20_ending = []
    top10_ski = []
    top10_range = []
    top10_shoot = []
    not_in_race = []
    dnf = [0, "0", "DSQ", "DNS", "DNF"]
    is_relay = race_type in ['RL', 'SR']
    print(race_type)
    if is_relay:
        athlete_key = "relayTeams"
    else:
        athlete_key = "athletes"
    country_key = "nat"  # is_relay ? "nat" : "nation"
    has_penalty = race_type in ['SP', 'IN']
    for rez in results[athlete_key]:
        if is_relay:
            loops = len(rez['individualShots']) * 5 - rez['hits']
            spares = rez['shots'] - len(rez['individualShots']) * 5
            shooting = f"{rez['hits']}(+{spares})/{len(rez['individualShots']) * 5}"
            if loops > 0:
                shooting = f"{shooting} (+{loops} loop)"
        else:
            shooting = f"{rez['hits']}/{rez['shots']}"
        if rez['rank'] in dnf:
            not_in_race.append(dict({'rank': rez['resultString'], 'name': rez['nameMeta'], 'time': rez['totalTime'],
                                     'country': rez[country_key], 'shooting': shooting}))
        elif int(rez['rank']) <= 20:
            top20_ending.append(dict({'rank': int(rez['rank']), 'name': rez['nameMeta'], 'time': rez['totalTime'],
                                      'country': rez[country_key], 'shooting': shooting}))
        for meta in rez['metaStats']:
            category = meta.get('category', '')
            if meta['rank'] == 1:
                endtime = time.strftime('%H:%M:%S', time.gmtime(meta['value']))
            else:
                endtime = meta['behind']

            if category and category == "Course Total Time":
                if meta['rank'] <= 10 and meta['rank'] not in dnf:
                    top10_ski.append(dict(
                        {'rank': meta['rank'], 'name': rez['nameMeta'], 'time': endtime, 'country': rez[country_key],
                         'shooting': shooting}))
            elif category and category == "Range Total Time":
                if meta['rank'] <= 10 and meta['rank'] not in dnf:
                    if has_penalty:
                        if race_type == 'SP':
                            penalty = 0
                            for pen in rez['individualShots']:
                                if pen['penaltyLapsCount'] > 0:
                                    penalty += pen['penaltyTime']
                            penalty = time.strftime('%M:%S', time.gmtime(penalty))
                        elif race_type == 'IN':
                            penalty = 0
                            for pen in rez['individualShots']:
                                if pen['missedShots'] > 0:
                                    penalty += pen['penaltyTime']
                            penalty = time.strftime('%M:%S', time.gmtime(penalty))
                        else:
                            penalty = time.strftime('%M:%S', time.gmtime(rez['penaltytime']['time']))
                    else:
                        penalty = 0
                    top10_range.append(dict(
                        {'rank': meta['rank'], 'name': rez['nameMeta'], 'time': endtime, 'country': rez[country_key],
                         'shooting': shooting, 'penalty_time': penalty}))
            elif meta['category'] and meta['category'] == "Shooting Total Time":
                if meta['rank'] <= 10 and meta['rank'] not in dnf:
                    top10_shoot.append(dict({'rank': meta['rank'], 'name': rez['nameMeta'], 'time': meta['value'],
                                             'country': rez[country_key], 'shooting': shooting}))

    out = ("Welcome to the stats for the " + results['shortDescription'] +
           ' in ' + results['eventOrganizer'] +
           ' on this ' + datetime.utcfromtimestamp(results['time']).strftime('%d %B %Y') +
           '\n\n')
    out += weather(results)
    out += podium(sorted(top20_ending, key=lambda d: d['rank']))
    out += reddit_format("The top 20 results from " + results['shortDescription'],
                         sorted(top20_ending, key=lambda d: d['rank']))
    out += reddit_format("Top 10 fastest shooters:", sorted(top10_shoot, key=lambda d: d['rank']), 1, is_relay)
    out += reddit_format("Top 10 fastest on the range:", sorted(top10_range, key=lambda d: d['rank']), 1, is_relay,
                         has_penalty)
    out += reddit_format("Top 10 fastest skiers:", sorted(top10_ski, key=lambda d: d['rank']))
    if len(not_in_race) > 0:
        out += reddit_format_dsq("Dit not Finish or start:", not_in_race, results['juryDecisions'])
    out += ("\n\n------\n\n^^I'm ^^just ^^a ^^bot,"
            " ^^https://github.com/biabot/reddit_biabot ^^if ^^you ^^want ^^to ^^know ^^more")

    return out


def weather(data):
    return f"The weather at the time of the race: Air temp {data['weather']['afterStart']['airTemperature']}°C, Snow temp {data['weather']['afterStart']['snowTemperature']}°C , wind at range {data['weather']['afterStart']['wind']}\n\n"


def podium(data):
    out = "\n\nToday's Podium :\n\n"
    for da in data:
        if int(da['rank']) <= 3:
            out += f"{da['rank']}. {da['name']}\n\n"
    out += "\n"
    return out


def reddit_format(title, data, shooting=False, is_relay=False, penalty=False):
    out = f"**{title}**\n"
    out += "\n"
    if shooting:
        if penalty:
            out += "|\#|Athlete|Time|shooting|with penalty|\n"
            out += "|:-|:-|:-|:-|:-|\n"
        else:
            out += "|\#|Athlete|Time|shooting|\n"
            out += "|:-|:-|:-|:-|\n"
    else:
        out += "|\#|Athlete|Country|Time|\n"
        out += "|:-|:-|:-|:-|\n"
    for da in data:
        if shooting:
            if penalty:
                out += f"|{da['rank']}| {da['name']} |{da['time']}|{da['shooting']}|+{da['penalty_time']}\n"
            else:
                out += f"|{da['rank']}| {da['name']} |{da['time']}|{da['shooting']}\n"
        else:
            out += f"|{da['rank']}| {da['name']} |{da['country']}|{da['time']}\n"
    out += "\n"
    out += "&#x200B;\n"
    return (out)


def reddit_format_dsq(title, data, jury=""):
    out = f"**{title}**\n"
    out += "\n"
    out += "|\#|Athlete|Country|\n"
    out += "|:-|:-|:-|\n"
    for da in data:
        out += f"|{da['rank']}| {da['name']} |{da['country']}\n"
    if jury != '' and jury != ['none']:
        out += "\n **Jury Decision(s)**: \n\n"
        for jur in jury:
            out += jur + "\n"
    out += "\n"
    out += "&#x200B;\n"
    return (out)


if __name__ == "__main__":
    main()
