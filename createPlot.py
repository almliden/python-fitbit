import configparser
import datetime
import time
import sys
import os
from databaseConnection import DatabaseConnection, DatabaseConfigurator
from bson.json_util import dumps, loads
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import array
import helper_functions
import io
import requests
import base64

class PlotterConfig:
  api_url:str = ''
  api_key=str = ''

class Plotter:
  conf:PlotterConfig = None
  def __init__(self, conf:PlotterConfig):
    if (conf != None):
      self.conf = conf

  def _zip_timeseries(self, heart_series, step_series):
    vals = []
    missing_values = []
    for h, s in zip(heart_series, step_series):
      ht = datetime.datetime.fromisoformat('2000-01-01 ' + h['time'])
      st = datetime.datetime.fromisoformat('2000-01-01 ' + s['time'])
      if ( ht.hour != st.hour and ht.minute != st.minute ):
        missing_values.append( { 'heart': h, 'step': s } )
      else:
        vals.append({'time': s['time'], 'heart': h['value'], 'steps': s['value']})
    return vals

  def plot_heart_steps(self, step_series, heart_series, path_to_save, save_file=False, show_graph=False, upload=False):
    if (save_file == show_graph and save_file == upload ):
      raise Exception('Argument Exception. Incompatible arguments found. Conflicting instructions.')
    elif (save_file and (show_graph or upload)):
      raise Exception('Argument Exception. Incompatible arguments found. No valid instruction present.')
    elif (show_graph and (save_file or upload)):
      raise Exception('Argument Exception. Incompatible arguments found. No valid instruction present.')

    if (save_file or upload):
      matplotlib.use('Agg')
    matplotlib.style.use('ggplot')

    normalized_by_minute = self._normalize_by_minute(heart_series)
    heart_normalized_series = self._set_median_by_minute(normalized_by_minute)

    zipped_timeseries = self._zip_timeseries(heart_normalized_series, step_series)
    
    combined = pd.DataFrame(data=zipped_timeseries)
    combined.plot.line(x='time', y=['heart', 'steps'], rot=90)

    if (save_file == True or show_graph == True):
      plt.legend()
      plt.show()
    
    if (save_file == True):
      file_path = '{path}.png'.format(path = path_to_save)
      plt.savefig(file_path, transparent=True, bbox_inches='tight')
      return file_path

    if (show_graph == True):
      return ''

    if (upload == True):
      fig1 = plt.gcf()
      plt.show()
      plt.draw()
      img_data = io.BytesIO()
      fig1.savefig(img_data, transparent=True, bbox_inches='tight', format='png')
      img_data.seek(0)
      base64_bytes = base64.b64encode(img_data.getvalue())
      return self._upload_image(base64_bytes)
      
  def _upload_image(self, base64_encoded_image:str):
      url='{url}&key={key}&name={name}'.format(url= self.conf.api_url, key = self.conf.api_key, name = helper_functions.file_friendly_time_stamp() )
      response = requests.post(url, data={ 'image': base64_encoded_image })
      return response.text
      
  def _format_minute(self, minute:str):
    if (len(minute) == 2):
      return minute
    return '0'+minute
  
  ## Fill in with data if it's missing? (Average between minutes?)
  def _normalize_by_minute(self, time_series):
    start_time = datetime.datetime.fromisoformat('2000-01-01 ' + time_series[0]['time'])
    start_minute = start_time.minute
    series = []
    for time in time_series:
      if (int(time['time'][3:5]) > start_minute):
        start_minute = int(time['time'][3:5])
      elif (int(time['time'][3:5]) == 0):
        start_minute = 0
      val = { 'time' : '{hour}:{minute}:00'.format(hour=time['time'][0:2], minute=self._format_minute(str(start_minute))), 'value': time['value'] }
      series.append(val)
    return series

  def _set_median_by_minute(self, time_series):
    current_element = time_series[0]
    result = []
    temporary = []
    for time in time_series:
      if (time['time'] == current_element['time']):
        temporary.append(time)
      else:
        median = self._get_median_in_series(temporary)
        result.append({ 'time': time['time'], 'value': median})
        temporary.clear()
        temporary.append(time)
        current_element = time
    return result

  def _get_median_in_series(self, series):
    values = []
    for val in series: 
      values.append(val['value'])
    values.sort()
    return values[round(len(values) / 2)]

def main():
  database_context = DatabaseConnection(DatabaseConfigurator('config.ini').Config())
  database = database_context.connect()

  parser=configparser.ConfigParser()
  parser.read('config.ini')

  IMAGE_API_KEY=parser.get('Image Hosting', 'IMAGE_API_KEY')
  IMAGE_API_URL=parser.get('Image Hosting', 'IMAGE_API_URL')

  search_date = datetime.date.today() - datetime.timedelta(days=1)
  yesterdate_steps = database.steps.find_one({'activities-steps.dateTime' : search_date.isoformat() })
  time_series_steps = yesterdate_steps['activities-steps-intraday']['dataset']
  yesterdate_heart = database.heart.find_one({'activities-heart.dateTime' : search_date.isoformat() })
  time_series_heart = yesterdate_heart['activities-heart-intraday']['dataset']

  conf = PlotterConfig()
  conf.api_key = IMAGE_API_KEY
  conf.api_url = IMAGE_API_URL+'?expiration=36000'
  plotter = Plotter(conf)
  show_graph=False
  save_file=True
  upload=False
  raw_response = plotter.plot_heart_steps(time_series_steps, time_series_heart, helper_functions.file_friendly_time_stamp()+'_heart',show_graph=show_graph, save_file=save_file, upload=upload)
  if (upload):
    response = loads(raw_response)
    inserted = database.bb_images.insert_one({ helper_functions.file_friendly_time_stamp()+'_heart' : response })
    if (not inserted.acknowledged):
      print("Problem writing to database.")
  elif (save_file):
    print('File saved! Name: ' + raw_response)

  database_context.disconnect()
  sys.exit()
  os._exit(1)

if __name__ == "__main__":
    main()
