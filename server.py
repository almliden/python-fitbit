from databaseConnection import DatabaseConnection, DatabaseConfigurator
from fastapi import FastAPI
from starlette.requests import Request
import datetime

from bson import BSON
from bson import json_util
from bson.json_util import dumps, loads

app = FastAPI()
databaseConfig = DatabaseConfigurator('config.ini')
dbcontext = DatabaseConnection(databaseConfig.Config())
db = dbcontext.connect()

@app.get("/me")
def me(request: Request):
  user = db.user_tokens.find_one({}, {'_id': 1, 'user' : 1})
  return user['user']

@app.get("/heartrate/{date}")
def heartRateByDate(request: Request, date):
  heartrates = db.heart.find(
    { "activities-heart.dateTime": date },
    {
      '_id': 0,
      'activities-heart.dateTime': 1,
      'activities-heart.value.restingHeartRate': 1,
      'activities-heart-intraday.dataset' : 1
      # get the whole object
      # , 'activities-heart': 1, 'activities-heart-intraday': 1
    }
  )
  dd = {'heartRates' : list(heartrates) }
  return dd

@app.get("/heartrate/{startDate}/{endDate}")
def heartRateByDateRange(request: Request, startDate, endDate):
  heartrates = db.heart.find(
    {'activities-heart.dateTime': {'$in':  getDates(startDate, endDate)}},
    # {'activities-heart.dateTime': {'$lte': end, '$gte': start}},
    # { "activities-heart.dateTime": startDate },
    # {'$lt': end, '$gte': start}
    {
      '_id': 0,
      'activities-heart.dateTime': 1,
      'activities-heart.value.restingHeartRate': 1,
      'activities-heart-intraday.dataset' : 1
      # get the whole object
      # , 'activities-heart': 1, 'activities-heart-intraday': 1
    }
  )
  dd = {'heartRates' : list(heartrates) }
  return dd

def getDates(startDate, endDate):
  start = datetime.datetime.fromisoformat(startDate)
  end = datetime.datetime.fromisoformat(endDate)
  timedelta = end - start
  days = int(timedelta.total_seconds()/3600/24)+1
  date_list = [datetime.datetime.isoformat(end - datetime.timedelta(days=x))[0:10] for x in range(days)]
  return date_list

@app.get("/heartrate/aggregated/{startDate}/{endDate}")
def heartRateAggregatedByDateRange(request: Request, startDate, endDate):
  pipeline = [
    { "$match": {'activities-heart.dateTime': {'$in': getDates(startDate, endDate)}}},
    { "$unwind" : "$activities-heart-intraday.dataset"},
    {
      "$group": {
        "_id" : "$activities-heart.dateTime",
        "averageHeartRate": { "$avg" : "$activities-heart-intraday.dataset.value" },
        "restingHeartRate": { "$min": "$activities-heart.value.restingHeartRate"},
        "max" : { "$max" : "$activities-heart-intraday.dataset.value" },
        "min" : { "$min" : "$activities-heart-intraday.dataset.value" },
        "date" : { "$first" : "$activities-heart.dateTime" }
      }
    },
    {
      "$sort" : { "date": 1 }
    }
  ]
  heartrates = db.heart.aggregate(pipeline)
  return {'heartRates' : heartrates['result'] }

@app.get("/heartrate/calculated/{startDate}/{endDate}")
def heartRateCalculatedByDateRange(request: Request, startDate, endDate):
  rates = loads(heartRateByDateRange(request, startDate, endDate))
  print(rates)
  return {'heartRates' : rates }