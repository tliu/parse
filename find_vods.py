import pytz
import json
from urllib.request import Request, urlopen
import datetime

offset = 10
#(start, end, id)

def parse_tz_date(s):
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S%z')

kill_time = datetime.datetime(2018, 10, 31, 20, 0)
tz = pytz.timezone("America/New_York")
localized_kill = tz.localize(kill_time)

url = "https://api.twitch.tv/kraken/channels/60056333/videos?limit=100&broadcast_type=archive"
headers = {
    "Client-ID": "5apd693hdygyetndq8edhjzebxigr5",
    "Accept": "application/vnd.twitchtv.v5+json"
}

req = Request(url)

for header, val in headers.items():
    req.add_header(header, val)

videos = []

with urlopen(req) as url:
    data = json.loads(url.read().decode())
    for v in data["videos"]:
        if (v["length"] > 90000):
            continue
        date = parse_tz_date(v["created_at"])
        end = date + datetime.timedelta(seconds=v["length"])
        videos.append((date, end, v["_id"], v["url"]))

vods = [v for v in videos if localized_kill >= v[0] and localized_kill <= v[1]]
for v in vods:
    print(v[3] + "?t=%ds" % ((localized_kill - v[0]).seconds - offset))

