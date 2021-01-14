from datetime import date, datetime, timedelta

class GeneratePreview:
  def __init__(self):
    self.template_file_name = './email_templates/template.html'
    self.template_folder = './email_templates'
    self.buttonHref = '#'

  def addHeartRate(self, heartRate = 50):
    with open('{folderPath}/restingHeartRate.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
      return fopen.read().format(section_text = 'This was your resting heart rate.', section_number = heartRate)

  def addDistance(self, distance = '5.3456345'):
    with open('{folderPath}/distance.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
      return fopen.read().format(section_text = 'This is your calculated distance.', section_number = round(float(distance), 3))

  def addSteps(self, steps=8000):
    selectedPhrase = 'That\'s great!'
    with open('{folderPath}/totalSteps.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
      return fopen.read().format(section_text = 'You took this many steps. %s The recommended number of steps per day is 10 000, but we settle for 8000 to keep our goals reasonable.' % selectedPhrase, section_number = steps)

  def addStepsHeartDistance(self, steps=8135, heart=50, distance='6.23'):
    with open('{folderPath}/heartStepsDistance.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
      return fopen.read().format(steps=steps, distance=distance, heartrate=heart)

  def addMeditate(self, btnLocation):
    with open('{folderPath}/meditate.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
      return fopen.read().format(section_text='Meditation sets the mood for the day. Do you have time to spare?',
         button_location=btnLocation, button_text='Take me there!')

  def addYesterDaySleep(self, btnLocation):
    with open('{folderPath}/meditate.html'.format(folderPath=self.template_folder), 'r', -1) as fopen:
      return fopen.read().format(section_text='Meditation sets the mood for the day. Do you have time to spare?',
         button_location=btnLocation, button_text='Take me there!')

  def createPreview(self):
    today = date.today().isoformat()
    yesterDate = date.today() - timedelta(days=1)
    emailParts = {}
    emailParts['restingHeartRate'] = self.addHeartRate()
    emailParts['steps'] = self.addSteps()
    emailParts['distance'] = self.addDistance()
    # emailParts['addStepsHeartDistance'] = self.addStepsHeartDistance()
    emailParts['meditate2'] = self.addMeditate('headspace://home')

    sections_content = ''
    for key, value in emailParts.items():
      if (value != ''):
        sections_content += value

    with open(self.template_file_name, 'r', -1) as fopen:
      message = fopen.read().format(
        date=today,
        title='Daily report',
        sections=sections_content,
        button_text='View more stats!',
        button_location=self.buttonHref)
      with open('{path}/generated.html'.format(path=self.template_folder), 'w', -1) as fwrite:
        fwrite.writelines(message)
        print("Updated!")

generator = GeneratePreview()
generator.createPreview()

