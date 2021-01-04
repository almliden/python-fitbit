import gather_keys_oauth2 as Oauth2
import fitbit
import pandas as pd
import datetime
import configparser
import json

parser = configparser.ConfigParser()
parser.read('config.ini')
CLIENT_ID = parser.get('Login Parameters', 'CLIENT_ID')
CLIENT_SECRET = parser.get('Login Parameters', 'CLIENT_SECRET')

server=Oauth2.OAuth2Server(CLIENT_ID, CLIENT_SECRET)
server.browser_authorize()
ACCESS_TOKEN=str(server.fitbit.client.session.token['access_token'])
REFRESH_TOKEN=str(server.fitbit.client.session.token['refresh_token'])
auth2_client=fitbit.Fitbit(CLIENT_ID,CLIENT_SECRET,oauth2=True,access_token=ACCESS_TOKEN,refresh_token=REFRESH_TOKEN)

dateRange = [
  # datetime.date(2020, 12, 24),
  # datetime.date(2020, 12, 25),
  # datetime.date(2020, 12, 26),
  # datetime.date(2020, 12, 27),
  # datetime.date(2020, 12, 28),
  # datetime.date(2020, 12, 29),

  datetime.date(2020, 12, 30)
]

for currentDate in dateRange:
  date = currentDate.isoformat()
  oneDayData = auth2_client.sleep(date)
  with open(date + '_sleep.json', 'w') as outfile:
    json.dump(oneDayData, outfile)
