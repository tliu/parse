from __future__ import print_function
import sys
import struct 
from collections import defaultdict
from urllib.request import Request, urlopen
import urllib.error
import re
import json
import enum
import datetime
import os
import pytz

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

players = ["fancy badger", "fancy dook", "ryanhfung", "Helvetica_j", "TTalus"]

class Game:
    def __init__(self, filename):
        self.filename = filename
        self.elims = defaultdict(lambda: [])
    
    def add_elim(self, killer, killed, time):
        self.elims[killer].append((killed, time))


class ForniteReader:
    def __init__(self, filename):
        self.reader = open(filename, "rb")
        self.reader.seek(0, 2)
        self.file_size = self.reader.tell()
        self.reader.seek(0)

    def uint32(self):
        return struct.unpack("I", self.reader.read(4))[0]

    def int32(self):
        return struct.unpack("i", self.reader.read(4))[0]

    def int64(self):
        return struct.unpack("L", self.reader.read(8))[0]

    def string(self):
        length = self.int32()
        # unicode
        if length < 0:
            length = -length
            data = self.reader.read(length * 2)
            unpacked = struct.unpack(str(2 * length) + "s", data)[0]
            return str(unpacked.decode("utf-16")).strip().rstrip('\x00')
        else:
            data = self.reader.read(length)
            unpacked = struct.unpack(str(length) + "s", data)[0]
            return str(unpacked.decode("utf-8")).strip().rstrip('\x00')

    def skip(self, num):
        self.reader.seek(num, 1)

    def has_more(self):
        return self.reader.tell() < self.file_size

class ChunkType(enum.IntEnum): 
    Header = 0
    ReplayData = 1
    Checkpoint = 2
    Event = 3
    Unknown = 0xFFFFFFFF

class VersionHistory(enum.IntEnum):
    HISTORY_INITIAL                         = 0
    HISTORY_FIXEDSIZE_FRIENDLY_NAME         = 1
    HISTORY_COMPRESSION                     = 2
    HISTORY_RECORDED_TIMESTAMP              = 3

path = os.getcwd() + "/replays/"
g = Game("database")
for filename in os.listdir(path):
    r = ForniteReader(path + filename)
    file_magic = 0x1CA2E27F

    magic = r.uint32()
    if file_magic != magic:
        eprint("Invalid replay file!")
        exit(1)

    file_version = r.uint32()
    length_ms = r.uint32()
    net_version = r.uint32()
    changelist = r.uint32()

    name = r.string()
    is_live = r.uint32() != 0

    if file_version >= VersionHistory.HISTORY_RECORDED_TIMESTAMP:
        ticks = r.int64()
        game_time = datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds = ticks/10)
        

    if file_version >= VersionHistory.HISTORY_COMPRESSION:
        compressed = r.uint32() != 0


    while r.has_more():
        chunk_type = r.uint32()
        chunk_size = r.int32()
        offset = r.reader.tell()
        
        if chunk_type == ChunkType.Event:
            chunk_id = r.string()
            group = r.string()
            meta = r.string()
            time1 = r.uint32()
            time2 = r.uint32()
            size = r.int32()
            if "playerElim" in group:
                r.skip(45)
                killed = r.string()
                killer = r.string()
                g.add_elim(killer, killed, game_time + datetime.timedelta(milliseconds=time1))

        r.reader.seek(offset + chunk_size, 0)


def strip_non_ascii(string):
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)

def guess_twitch(epic_name):
    name = strip_non_ascii(epic_name.lower())
    name = re.sub("_$", "@", name)
    for fix in fixes:
        name = re.sub(fix + "$", "", name)
        name = re.sub("^" + fix, "", name)
    name = re.sub("\.", "", name)
    name = re.sub("_$", "", name)
    name = re.sub("^_*", "", name)
    name = re.sub("@", "_", name)
    name = re.sub("\s", "", name)
    name = re.sub("^-", "", name)
    name = re.sub("-$", "", name)
    name = re.sub("-", "_", name)
    name = re.sub(r'[^\w_]', "", name)
    return name.strip()

user_url = "https://api.twitch.tv/helix/users?"
headers = {
    "Client-ID": "5apd693hdygyetndq8edhjzebxigr5",
    "Accept": "application/vnd.twitchtv.v5+json"
}

fixes = ["twitch", "ttv", "tv", "yt", "youtube"]
kill_list = []

for killer in g.elims.keys():
    if killer in players:
        kills = g.elims[killer]
        for kill in kills:
            if kill[0] != killer:
                guess = guess_twitch(kill[0])
                kill_list.append({
                    "killer": killer,
                    "guess": guess,
                    "kill_time": kill[1],
                    "epic": kill[0],
                    "twitch": None,
                    "vod": None
                })

f = list(set([k["guess"] for k in kill_list if len(k["guess"]) > 0]))

s = f[:100]
while len(s) > 0:
    users = "login=" + ("&login=".join(s))

    req = Request(user_url + users)

    for header, val in headers.items():
        req.add_header(header, val)

    try:
        with urlopen(req) as url:
            data = json.loads(url.read().decode())
            for u in data["data"]:
                name = u["login"]
                twitch_id = u["id"]
                for k in kill_list:
                    if k["guess"] == name:
                        k["twitch"] = twitch_id
    except urllib.error.HTTPError as error:
        eprint("----------------ERROR---------------------")
        eprint(user_url + users)
        eprint(error.read())
    f = f[100:]
    s = f[:100]

OFFSET_SECONDS = 10

utc = pytz.utc
def parse_tz_date(s):
    return utc.localize(datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ'))

vod_url = "https://api.twitch.tv/kraken/channels/%s/videos?limit=100&broadcast_type=archive"

cache = {}

tz = pytz.timezone("America/New_York")
for k in kill_list:
    if k["twitch"] != None:
        guess = k["guess"]
        eprint("checking vods for " + guess)
        k["kill_time"] = tz.localize(k["kill_time"])
        localized_kill = k["kill_time"]

        data = None
        videos = []

        if not guess in cache.keys():
            req = Request(vod_url % k["twitch"])

            for header, val in headers.items():
                req.add_header(header, val)

            with urlopen(req) as url:
                data = json.loads(url.read().decode())
                cache[guess] = data

        else:
            data = cache[guess]
            eprint("found in cache")

        if data != None:
            for v in data["videos"]:
                if (v["length"] > 90000):
                    continue
                date = parse_tz_date(v["created_at"])
                end = date + datetime.timedelta(seconds=v["length"])
                videos.append((date, end, v["_id"], v["url"]))

        vods = [v for v in videos if localized_kill >= v[0] and localized_kill <= v[1]]
        for v in vods:
            k["vod"] = v[3] + "?t=%ds" % ((localized_kill - v[0]).seconds - OFFSET_SECONDS)

for k in kill_list:
    k["kill_time"] = k["kill_time"].timestamp()

j = [k for k in kill_list if k["vod"] != None or k["twitch"] != None]
print("<html>")
print("""<head><style>
table, th, td {
  border: 1px solid black;
  }</style></head>
  """)
print("<body>")
print("<table style='width: 100%;'><tr>")
print("<th>Killer</th>")
print("<th>Killed</th>")
print("<th>Twitch Guess</th>")
print("<th>Kill Time</th>")
print("<th>Twitch ID</th>")
print("<th>VOD Link</th>")
print("</tr>")
for kill in j:
  print("<tr>")
  print("<td>" + str(kill["killer"]) + "</td>")
  print("<td>" + str(kill["epic"]) + "</td>")
  print("<td>" + str(kill["guess"]) + "</td>")
  time = kill["kill_time"]
  time = datetime.datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S.%f') 
  print("<td>" + time + "</td>")
  print("<td>" + str(kill["twitch"]) + "</td>")
  vod = kill["vod"]
  if vod != None:
      print("<td><a href=%s>%s</a></td>" % (vod, vod))
  print("</tr>")

print("</table></body></html>")



  #"killer": killer,
  #"guess": guess,
  #"kill_time": kill[1],
  #"epic": kill[0],
  #"twitch": None,
  #"vod": None



