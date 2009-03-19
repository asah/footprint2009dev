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

import urllib2, urllib
import logging
from google.appengine.api import urlfetch

API_SSL_SERVER="https://api-secure.recaptcha.net"
API_SERVER="http://api.recaptcha.net"
VERIFY_SERVER="api-verify.recaptcha.net"

class RecaptchaResponse(object):
    def __init__(self, is_valid, error_code=None):
        self.is_valid = is_valid
        self.error_code = error_code

def displayhtml (public_key,
                 use_ssl = False,
                 error = None):
    """Gets the HTML to display for reCAPTCHA

    public_key -- The public api key
    use_ssl -- Should the request be sent over ssl?
    error -- An error message to display (from RecaptchaResponse.error_code)"""

    error_param = ''
    if error:
        error_param = '&error=%s' % error

    if use_ssl:
        server = API_SSL_SERVER
    else:
        server = API_SERVER

    return """<script type="text/javascript" src="%(ApiServer)s/challenge?k=%(PublicKey)s%(ErrorParam)s"></script>

<noscript>
  <iframe src="%(ApiServer)s/noscript?k=%(PublicKey)s%(ErrorParam)s" height="300" width="500" frameborder="0"></iframe><br />
  <textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
  <input type='hidden' name='recaptcha_response_field' value='manual_challenge' />
</noscript>
""" % {
        'ApiServer' : server,
        'PublicKey' : public_key,
        'ErrorParam' : error_param,
        }


def submit (recaptcha_challenge_field,
            recaptcha_response_field,
            private_key,
            remoteip):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse
    for the request

    recaptcha_challenge_field -- The value of recaptcha_challenge_field from the form
    recaptcha_response_field -- The value of recaptcha_response_field from the form
    private_key -- your reCAPTCHA private key
    remoteip -- the user's ip address
    """

    logging.info("submit")
    if not (recaptcha_response_field and recaptcha_challenge_field and
            len (recaptcha_response_field) and len (recaptcha_challenge_field)):
        logging.info("incorrect-captcha-sol")
        return RecaptchaResponse (is_valid = False, error_code = 'incorrect-captcha-sol')
    
    def encode_if_necessary(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    params = urllib.urlencode ({
            'privatekey': encode_if_necessary(private_key),
            'remoteip' :  encode_if_necessary(remoteip),
            'challenge':  encode_if_necessary(recaptcha_challenge_field),
            'response' :  encode_if_necessary(recaptcha_response_field),
            })
    logging.info("calling recaptcha: "+params)

    resp = urlfetch.fetch(url="http://%s/verify" % VERIFY_SERVER,
                          payload=params,
                          method=urlfetch.POST,
                          headers={'Content-Type': 'application/x-www-form-urlencoded'})

    #request = urllib2.Request (
    #    url = "http://%s/verify" % VERIFY_SERVER,
    #    data = params,
    #    headers = {
    #        "Content-type": "application/x-www-form-urlencoded",
    #        "User-agent": "reCAPTCHA Python"
    #        }
    #    )
    #httpresp = urllib2.urlopen (request)
    #return_values = httpresp.read ().splitlines ();
    return_values = resp.content.splitlines ();
    #httpresp.close();
    return_code = return_values[0]
    if return_code == "true":
        return RecaptchaResponse (is_valid=True)
    return RecaptchaResponse (is_valid=False, error_code=return_values[1])


