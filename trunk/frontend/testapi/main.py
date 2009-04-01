# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cgi
import sys
import os

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

import testapi.helpers

class DumpSampleData(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__),
                        testapi.helpers.CURRENT_STATIC_XML)
    f = open(path, 'r')
    self.response.headers['Content-Type'] = 'text/xml'
    self.response.out.write(f.read())

class RunTests(webapp.RequestHandler):
  def get(self):
    testType = self.request.get('test_type') or 'all'
    responseTypes = self.request.get('response_types') or \
        testapi.helpers.DEFAULT_RESPONSE_TYPES
    remoteUrl = self.request.get('url') or ''
    specialOutput = self.request.get('output') or ''
    errors = ''
    
    if specialOutput == 'test_types':
      self.response.out.write(testapi.helpers.ALL_TEST_TYPES)
      return

    if remoteUrl == '':
      errors = 'No remote url given in request, using default url'
      apiUrl = testapi.helpers.DEFAULT_TEST_URL
    else:
      apiUrl = remoteUrl
        
    outstr = ""
    outstr += '<style>'
    outstr += 'p {font-family: Arial, sans-serif; font-size: 10pt; margin: 0;}'
    outstr += 'p.error {color: #880000;}'
    outstr += '.test {font-size: 12pt; font-weight: bold; margin-top: 12px;}'
    outstr += '.uri {font-size: 10pt; font-weight: normal; color: gray;'
    outstr += '      margin-left: 0px;}'
    outstr += '.result {font-size: 11pt; font-weight: normal; '
    outstr += '      margin-left: 8px; margin-bottom: 4px;}'
    outstr += '.fail {color: #880000;}'
    outstr += '.success {color: #008800;}'
    outstr += '.amplification {color: gray; margin-left: 16px;}'
    outstr += '</style>'
    outstr += '<h1>Running test: ' + testType + '</h1>'
    outstr += '<p class="error">' + errors + '</p>'
    outstr += '<p>Response types: ' + responseTypes + '</p>'
    outstr += '<p>API url: ' + apiUrl + '</p>'
    self.response.out.write(outstr)

    responseTypes = responseTypes.split(',')
    for responseType in responseTypes:
      api_testing = testapi.helpers.ApiTesting(self)
      api_testing.run_tests(testType, apiUrl, responseType)
    

application = webapp.WSGIApplication(
  [('/testapi/run', RunTests),
   ('/testapi/sampleData.xml', DumpSampleData)],
  debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
