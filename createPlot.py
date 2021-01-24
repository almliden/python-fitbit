import configparser
import datetime
import time
import sys
import os
from databaseConnection import DatabaseConnection, DatabaseConfigurator
from bson.json_util import dumps, loads
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt ## NEW!
import array
import helperFunctions as helper_functions

class Plotter():
  # def __init__(self):

  ## PANDAS
  # heart_data = pd.DataFrame(data=yesterdate_heart['activities-heart-intraday']['dataset'])
  # step_data = pd.DataFrame(data=yesterdate_steps['activities-steps-intraday']['dataset'])
  # print(heart_data.head(3))
  # print(step_data.head(3))

  ## FORM: DataFrame.plot.bar(x=None, y=None, **kwargs)
  # time_and_value = heart_data[['time','value']].head(100)
  # time_and_value.plot.bar(x='time',y='value', rot=90)
  # plt.show()

  def PlotHeartStepData(self, step_series, heart_series, path_to_save):
    normalized_by_minute = self._normalize_by_minute(heart_series) #yesterdate_heart['activities-heart-intraday']['dataset'])
    heart_norm = self._set_median_by_minute(normalized_by_minute)
    # print(normalized_by_minute[0:10])
    # print(heart_norm[0:10])
    # for n in norm[0:20]:
    #   print(n)

    heart = heart_norm
    steps = step_series #yesterdate_steps['activities-steps-intraday']['dataset']

    vals = []
    for h, s in zip(heart, steps):
      vals.append({'time': s['time'], 'heart': h['value'], 'steps': s['value']})

    matplotlib.style.use('ggplot')
    axes = plt.gca()
    axes.set_ylim([0,220])

    combined = pd.DataFrame(data=vals)

    # combined.plot.bar(x='time', y=['heart','steps'], rot=90)
    # combined.plot.area(x='time', y=['heart', 'steps'], rot=90)
    # combined.plot.hist(x='time', y=['heart', 'steps'], rot=90)
    combined.plot.line(x='time', y=['heart', 'steps'], rot=90)

    # fig = plt.figure()

    # plt.legend()
    plt.show()
    # plt.plot()

    file_path = '{path}.png'.format(path = path_to_save)
    plt.savefig(file_path, transparent=True, bbox_inches='tight')
    # plt.savefig('{0}_heart.png'.format(helper_functions.file_friendly_time_stamp()), transparent=True, bbox_inches='tight')
    return file_path

  def _format_minute(self, minute:str):
    if (len(minute) == 2):
      return minute
    return '0'+minute
    
  def _normalize_by_minute(self, time_series):
    start_time = datetime.datetime.fromisoformat('2021-01-24 ' + time_series[0]['time'])
    start_minute = start_time.minute
    series = []
    for time in time_series:
      if (int(time['time'][3:5]) > start_minute):
        start_minute = int(time['time'][3:5])
      if (int(time['time'][3:5]) == 0):
        start_minute = 0
      val = { 'time' : '{hour}:{minute}:00'.format(hour=time['time'][0:2], minute=self._format_minute(str(start_minute))), 'value': time['value'] }
      series.append(val)
    return series

  def _set_median_by_minute(self, time_series):
    first = time_series[0]
    result = []
    temp = []
    for time in time_series:
      if (time['time'] == first['time']):
        temp.append(time)
      else:
        median = self._get_median_in_series(temp)
        result.append({ 'time': time['time'], 'value': median})
        temp.clear()
        temp.append(time)
        first = time
    return result

  def _get_median_in_series(self, series):
    values = []
    for val in series: 
      values.append(val['value'])
    values.sort()
    return values[round(len(values) / 2)]
    # series.sort(key = lambda value: value['value'])
    # return series[round(len(series) / 2)]

def main():
  # Initialize
  database_context = DatabaseConnection(DatabaseConfigurator('config.ini').Config())
  database = database_context.connect()

  parser=configparser.ConfigParser()
  parser.read('config.ini')

  # Main
  current_date = datetime.date.today()
  yester_date = datetime.date.today() - datetime.timedelta(days=1)
  search_date = yester_date

  # Lab
  yesterdate_steps = database.steps.find_one({'activities-steps.dateTime' : search_date.isoformat() })
  time_series_steps = yesterdate_steps['activities-steps-intraday']['dataset']

  yesterdate_heart = database.heart.find_one({'activities-heart.dateTime' : search_date.isoformat() })
  time_series_heart = yesterdate_heart['activities-heart-intraday']['dataset']

  plotter = Plotter()
  plotter.PlotHeartStepData(time_series_steps, time_series_heart, helper_functions.file_friendly_time_stamp()+'_heart')
  
  # Teardown
  database_context.disconnect()

  sys.exit()
  os._exit(1)

if __name__ == "__main__":
    main()
