import datetime

def get_dates(start:datetime.datetime, end:datetime.datetime):
  delta = end - start
  days = int(delta.total_seconds()/3600/24)+1
  date_list = [datetime.date.isoformat(end - datetime.timedelta(days=x))[0:10] for x in reversed(range(days)) ]
  return date_list

def get_dates_from_string(start:str, end:str):
  return get_dates(start=datetime.datetime.fromisoformat(start), end=datetime.datetime.fromisoformat(end))

def get_key(series, series_key, key):
  for i in range(0, len(series)):
    if (series[i][series_key] == key):
      return i
  return -1

def find_max_top(series, series_key = 'time', top = 3, lamba = lambda k: k['value']):
  items = []
  i = 0
  while (i <= top):
    m = max(series, key = lamba )
    items.append(m)
    idx = get_key(series, series_key, m[series_key])
    del series[idx]
    i += 1
  return items

def file_friendly_time_stamp():
  stamp = datetime.datetime.now().isoformat()
  return '{date}_{hour}-{minute}-{second}'.format(date=stamp[0:10], hour=stamp[11:13], minute=stamp[14:16], second=stamp[17:19])

# minutes = int(fitbitRateLimit['fitbitRateLimitReset'])/60
# seconds = 60 - (minutes % 60)