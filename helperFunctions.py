import datetime

def get_dates(start:datetime.datetime, end:datetime.datetime):
  delta = end - start
  days = int(delta.total_seconds()/3600/24)+1
  date_list = [datetime.date.isoformat(end - datetime.timedelta(days=x))[0:10] for x in reversed(range(days)) ]
  return date_list

def get_dates_from_string(start:str, end:str):
  return get_dates(start=datetime.datetime.fromisoformat(start), end=datetime.datetime.fromisoformat(end))

# minutes = int(fitbitRateLimit['fitbitRateLimitReset'])/60
# seconds = 60 - (minutes % 60)