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
    testType = self.request.get('test_type') or 'default'
    responseTypes = self.request.get('response_types') or testapi.helpers.DEFAULT_RESPONSE_TYPES
    remoteUrl = self.request.get('url') or ''
    errors = ''

    if remoteUrl == '':
      errors = 'No remote url given in request, using default url'
      apiUrl = testapi.helpers.DEFAULT_TEST_URL
    else:
      apiUrl = remoteUrl
        
    self.response.out.write('<style>')
    self.response.out.write('p {font-family: Arial, sans-serif; font-size: 10pt; margin: 0;}')
    self.response.out.write('p.error {color: #880000;}')
    self.response.out.write('.test {font-size: 12pt; font-weight: bold; margin-top: 12px;}')
    self.response.out.write('.uri {font-size: 10pt; font-weight: normal; color: gray; margin-left: 0px;}')
    self.response.out.write('.result {font-size: 11pt; font-weight: normal; margin-left: 8px; margin-bottom: 4px;}')
    self.response.out.write('.fail {color: #880000;}')
    self.response.out.write('.success {color: #008800;}')
    self.response.out.write('.amplification {color: gray; margin-left: 16px;}')
    self.response.out.write('</style>')
    self.response.out.write('<h1>Running test: ' + testType + '</h1>')
    self.response.out.write('<p class="error">' + errors + '</p>')
    self.response.out.write('<p>Response types: ' + responseTypes + '</p>')
    self.response.out.write('<p>API url: ' + apiUrl + '</p>')
    
    responseTypes = responseTypes.split(',')
    for responseType in responseTypes:
      testapi.helpers.RunTests(self, testType, apiUrl, responseType)
    

application = webapp.WSGIApplication([('/testapi/run', RunTests),
                                      ('/testapi/sampleData.xml', DumpSampleData)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
