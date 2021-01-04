import gather_keys_oauth2 as Oauth2
import fitbit
import pandas as pd
import datetime
import configparser

#Load Settings
parser = configparser.ConfigParser()
parser.read('config.ini')
consumer_key = parser.get('Login Parameters', 'C_KEY')
consumer_secret = parser.get('Login Parameters', 'C_SECRET')
CLIENT_ID=consumer_key
CLIENT_SECRET=consumer_secret

print(consumer_key)
print(consumer_secret)

# # #Setup an unauthorised client (e.g. with no user)
# unauth_client = fitbit.Fitbit(consumer_key, consumer_secret)
 
# # #Get data for a user
# user_params = unauth_client.user_profile_get(user_id='92659Y')

server=Oauth2.OAuth2Server(CLIENT_ID, CLIENT_SECRET)
server.browser_authorize()
ACCESS_TOKEN=str(server.fitbit.client.session.token['access_token'])
REFRESH_TOKEN=str(server.fitbit.client.session.token['refresh_token'])
auth2_client=fitbit.Fitbit(CLIENT_ID,CLIENT_SECRET,oauth2=True,access_token=ACCESS_TOKEN,refresh_token=REFRESH_TOKEN)

print(ACCESS_TOKEN)
print(REFRESH_TOKEN)
# This is the date of data that I want. 
# You will need to modify for the date you want

date_list = []
df_list = []

allDates = [
  datetime.date(2020, 12, 24),
  datetime.date(2020, 12, 25),
  datetime.date(2020, 12, 26),
  datetime.date(2020, 12, 27),
  datetime.date(2020, 12, 28),
  datetime.date(2020, 12, 29)
]

for oneDate in allDates:
  # oneDate = oneDate.date().strftime("%Y-%m-%d")
  oneDayData = auth2_client.intraday_time_series('activities/heart', base_date=oneDate, detail_level='1sec')
  df = pd.DataFrame(oneDayData['activities-heart-intraday']['dataset'])
  df.head()

  filename = oneDayData['activities-heart'][0]['dateTime'] +'_heart-rate_intradata'# Export file to csv
  df.to_csv(filename + '.csv', index = False)

  date_list.append(oneDate)
  df_list.append(df)
    
final_df_list = []

for date, df in zip(date_list, df_list):
    if len(df) == 0:
        continue
    df.loc[:, 'date'] = pd.to_datetime(date)
    final_df_list.append(df)

final_df = pd.concat(final_df_list, axis = 0)

final_df.tail()

filename = 'all_intradata'
final_df.to_csv(filename + '.csv', index = False)


# oneDate = datetime.date(2020, 12, 29)
# oneDayData = auth2_client.intraday_time_series('activities/heart', oneDate, detail_level='1sec')

# df = pd.DataFrame(oneDayData['activities-heart-intraday']['dataset'])
# df.head()

# filename = oneDayData['activities-heart'][0]['dateTime'] +'_intradata'# Export file to csv
# df.to_csv(filename + '.csv', index = False)
# # df.to_excel(filename + '.xlsx', index = False)
