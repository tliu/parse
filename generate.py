import sys
import datetime
import json

o = open(sys.argv[1])

j = json.loads(o.readline())

def print_html(j):
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


