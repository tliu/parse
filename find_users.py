from urllib.request import Request, urlopen
import re
import json

user_url = "https://api.twitch.tv/helix/users?"
headers = {
    "Client-ID": "5apd693hdygyetndq8edhjzebxigr5",
    "Accept": "application/vnd.twitchtv.v5+json"
}

#
# twitch foo, twitch_foo, ttv foo, tv foo
# remove twitch, tv, yt, ttv from name.  remove . or _ separating, don't remove _ if it's at the end

epic = ["twitch hispid", "twitch_tfue"]
fixes = ["twitch", "ttv", "tv", "yt", "youtube"]

def guess_twitch(epic_name):
    name = epic_name.lower()
    for fix in fixes:
        name = re.sub(fix + "$", "", name)
        name = re.sub("^" + fix, "", name)
    name = re.sub("\.", "", name)
    name = re.sub("_$", "", name)
    name = re.sub("^_", "", name)
    return name.strip()

guesses = {}

for name in epic:
    guess = guess_twitch(name)
    guesses[(guess, name)] = {
        "guess": guess,
        "epic": name,
        "twitch": None
    }

f = [v["guess"] for k, v in guesses.items()]

s = f[:100]
while len(s) > 0:
  users = "&login=".join(f)

  req = Request(user_url + users)

  for header, val in headers.items():
      req.add_header(header, val)

  with urlopen(req) as url:
      data = json.loads(url.read().decode())
      for u in data["data"]:
          name = u["login"]
          twitch_id = u["id"]
          for k in guesses.keys():
              if k[0] == name:
                  guesses[k]["twitch"] = twitch_id
  f = f[100:]
  s = f[:100]

print(guesses)
