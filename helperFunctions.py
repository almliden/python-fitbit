import datetime

def getDates(startDate, endDate):
  start = datetime.datetime.fromisoformat(startDate)
  end = datetime.datetime.fromisoformat(endDate)
  timedelta = end - start
  days = int(timedelta.total_seconds()/3600/24)+1
  date_list = [datetime.datetime.isoformat(end - datetime.timedelta(days=x))[0:10] for x in reversed(range(days)) ]
  return date_list

## Move out to some helper or utility class to sync historic data
# dates = getDates('2021-01-01', '2021-01-04')
# for date in dates:
#   dateToGet = datetime.date.fromisoformat(date)
#   getStepsForDate(dateToGet, auth2_client, db)


# minutes = int(fitbitRateLimit['fitbitRateLimitReset'])/60
# seconds = 60 - (minutes % 60)