import re
fixes = ['twitch']
def guess_twitch(epic_name):
    name = epic_name
    name = re.sub("_$", "@", name)
    for fix in fixes:
        name = re.sub(fix + "$", "", name)
        name = re.sub("^" + fix, "", name)
    name = re.sub("\.", "", name)
    name = re.sub("_$", "", name)
    name = re.sub("^_*", "", name)
    name = re.sub("@", "_", name)
    name = re.sub("\s", "", name)
    name = re.sub("-", "_", name)
    name = re.sub(r'[^\w_]', "", name)
    return name.strip()

print( guess_twitch("twitch_extrasaucex"))
