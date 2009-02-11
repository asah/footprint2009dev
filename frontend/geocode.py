from google.appengine.api import urlfetch
from xml.dom import minidom

def Geocode(address_plaintext):
  location = address_plaintext.replace(' ', '+')
  key = ''
  url = ('http://maps.google.com/maps/geo?q=%s&output=xml&key=%s' %
         (location, key))
  result = urlfetch.fetch(url)
  dom2 = minidom.parseString(result.content)
  geo_status = int(dom2.getElementsByTagName('code')[0].childNodes[0].data)

  #check to see if google was able to find the coordinates for the
  # street address
  if geo_status == 200:
      coord = dom2.getElementsByTagName('coordinates')[0].childNodes[0].data
      split_coord = coord.rsplit(',')
      longitude = (split_coord[0])
      latitude = (split_coord[1])

      accuracy = dom2.getElementsByTagName('AddressDetails')[0].getAttribute('Accuracy')

      return {'latitude': latitude,
              'longitude': longitude,
              'accuracy': accuracy
             }
