#!/usr/bin/env python
#

"""
script for loading into googlebase.
Usage: load_gbase.py username password
"""

import sys
import re
import logging
import subprocess
from datetime import datetime
import footprint_lib

USERNAME = ""
PASSWORD = ""

LOGPATH = "/home/footprint/public_html/datahub/dashboard/"
LOG_FN = LOGPATH + "load_gbase.log"
DETAILED_LOG_FN = LOGPATH + "load_gbase_detail.log"

# this file needs to be copied over to frontend/autocomplete/
POPULAR_WORDS_FN = "popular_words.txt"

STOPWORDS = set([
  'a', 'about', 'above', 'across', 'after', 'afterwards', 'again', 'against',
  'all', 'almost', 'alone', 'along', 'already', 'also', 'although', 'always',
  'am', 'among', 'amongst', 'amoungst', 'amount', 'an', 'and', 'another', 'any',
  'anyhow', 'anyone', 'anything', 'anyway', 'anywhere', 'are', 'around', 'as',
  'at', 'back', 'be', 'became', 'because', 'become', 'becomes', 'becoming',
  'been', 'before', 'beforehand', 'behind', 'being', 'below', 'beside',
  'besides', 'between', 'beyond', 'bill', 'both', 'bottom', 'but', 'by', 'call',
  'can', 'cannot', 'cant', 'co', 'computer', 'con', 'could', 'couldnt', 'cry',
  'de', 'describe', 'detail', 'do', 'done', 'down', 'due', 'during', 'each',
  'eg', 'eight', 'either', 'eleven', 'else', 'elsewhere', 'empty', 'enough',
  'etc', 'even', 'ever', 'every', 'everyone', 'everything', 'everywhere',
  'except', 'few', 'fifteen', 'fify', 'fill', 'find', 'fire', 'first', 'five',
  'for', 'former', 'formerly', 'forty', 'found', 'four', 'from', 'front','full',
  'further', 'get', 'give', 'go', 'had', 'has', 'hasnt', 'have', 'he', 'hence',
  'her', 'here', 'hereafter', 'hereby', 'herein', 'hereupon', 'hers', 'herself',
  'him', 'himself', 'his', 'how', 'however', 'hundred', 'i', 'ie', 'if', 'in',
  'inc', 'indeed', 'interest', 'into', 'is', 'it', 'its', 'itself', 'keep',
  'last', 'latter', 'latterly', 'least', 'less', 'ltd', 'made', 'many', 'may',
  'me', 'meanwhile', 'might', 'mill', 'mine', 'more', 'moreover', 'most',
  'mostly', 'move', 'much', 'must', 'my', 'myself', 'name', 'namely', 'neither',
  'never', 'nevertheless', 'next', 'nine', 'no', 'nobody', 'none', 'noone',
  'nor', 'not', 'nothing', 'now', 'nowhere', 'of', 'off', 'often', 'on', 'once',
  'one', 'only', 'onto', 'or', 'other', 'others', 'otherwise', 'our', 'ours',
  'ourselves', 'out', 'over', 'own', 'part', 'per', 'perhaps', 'please', 'put',
  'rather', 're', 'same', 'see', 'seem', 'seemed', 'seeming', 'seems',
  'serious', 'several', 'she', 'should', 'show', 'side', 'since', 'sincere',
  'six', 'sixty', 'so', 'some', 'somehow', 'someone', 'something', 'sometime',
  'sometimes', 'somewhere', 'still', 'such', 'system', 'take', 'ten', 'than',
  'that', 'the', 'their', 'them', 'themselves', 'then', 'thence', 'there',
  'thereafter', 'thereby', 'therefore', 'therein', 'thereupon', 'these', 'they',
  'thick', 'thin', 'third', 'this', 'those', 'though', 'three', 'through',
  'throughout', 'thru', 'thus', 'to', 'together', 'too', 'top', 'toward',
  'towards', 'twelve', 'twenty', 'two', 'un', 'under', 'until', 'up', 'upon',
  'us', 'very', 'via', 'was', 'we', 'well', 'were', 'what', 'whatever', 'when',
  'whence', 'whenever', 'where', 'whereafter', 'whereas', 'whereby', 'wherein',
  'whereupon', 'wherever', 'whether', 'which', 'while', 'whither', 'who',
  'whoever', 'whole', 'whom', 'whose', 'why', 'will', 'with', 'within',
  'without', 'would', 'yet', 'you', 'your', 'yours', 'yourself', 'yourselves',
  # custom stopwords for footprint
  'url', 'amp', 'quot', 'help', 'http', 'search', 'nbsp', 'need', 'cache',
  'vol', 'housingall', 'wantedall', 'personalsall', 'net', 'org', 'www',
  'gov', 'yes', 'no', '999',
  ])

def print_progress(msg):
  """print progress message-- shutup pylint"""
  print str(datetime.now())+": "+msg

KNOWN_WORDS = {}
def process_popular_words(name, url):
  """fetch this URL and update the dictionary of popular words."""
  # TODO: handle phrases (via whitelist, then later do something smart.
  print_progress("fetching %s from %s" % (name, url))
  urlfh = footprint_lib.open_input_filename(url)
  content = urlfh.read()
  urlfh.close()
  print_progress("cleaning content, %d bytes" % len(content))
  cleaner_regexp = re.compile('<[^>]*>', re.DOTALL)
  cleaned_content = re.sub(cleaner_regexp, '', content).lower()
  print_progress("splitting words, %d bytes" % len(cleaned_content))
  words = re.split(r'[^a-zA-Z0-9]+', cleaned_content)
  print_progress("loading words")
  for word in words:
    # ignore common english words
    if word in STOPWORDS:
      continue
    # ignore short words
    if len(word) <= 2:
      continue
    if word not in KNOWN_WORDS:
      KNOWN_WORDS[word] = 0
    KNOWN_WORDS[word] += 1
  print_progress("cleaning rare words from %d words" % len(KNOWN_WORDS))
  # clean to reduce ram needs
  for word in KNOWN_WORDS.keys():
    if KNOWN_WORDS[word] < 2:
      del KNOWN_WORDS[word]
  print_progress("done: word dict size %d words" % len(KNOWN_WORDS))

def append_log(outstr):
  """append to the detailed and truncated log, for stats collection."""
  outfh = open(DETAILED_LOG_FN, "a")
  outfh.write(outstr)
  outfh.close()

  outfh = open(LOG_FN, "a")
  for line in outstr.split('\n'):
    if re.search(r'(STATUS|ERROR)', line):
      outfh.write(line+"\n")
  outfh.close()

def error_exit(msg):
  """Print an error message to stderr and exit."""
  print >> sys.stderr, msg
  sys.exit(1)

# Use a shell for subcommands on Windows to get a PATH search.
USE_SHELL = sys.platform.startswith("win")

def run_shell_with_retcode(command, print_output=False,
                           universal_newlines=True):
  """Executes a command and returns the output from stdout and the return code.

  Args:
    command: Command to execute.
    print_output: If True, the output is printed to stdout.
                  If False, both stdout and stderr are ignored.
    universal_newlines: Use universal_newlines flag (default: True).

  Returns:
    Tuple (output, return code)
  """
  logging.info("Running %s", command)
  proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          shell=USE_SHELL,
                          universal_newlines=universal_newlines)
  if print_output:
    output_array = []
    while True:
      line = proc.stdout.readline()
      if not line:
        break
      print line.strip("\n")
      output_array.append(line)
    output = "".join(output_array)
  else:
    output = proc.stdout.read()
  proc.wait()
  errout = proc.stderr.read()
  if print_output and errout:
    print >> sys.stderr, errout
  proc.stdout.close()
  proc.stderr.close()
  append_log(output)
  append_log(errout)
  return output, errout, proc.returncode


def run_shell(command, silent_ok=False, universal_newlines=True,
              print_output=False):
  """run a shell command."""
  stdout, stderr, retcode = run_shell_with_retcode(command, print_output,
                                                   universal_newlines)
  #if retcode and retcode != 0:
  #error_exit("Got error status from %s:\n%s\n%s" % (command, stdout, stderr))
  if not silent_ok and not stdout:
    error_exit("No output from %s" % command)
  return stdout, stderr, retcode


def load_gbase(name, url):
  """shutup pylint."""
  print_progress("loading "+name+" from "+url)
  # run as a subprocess so we can ignore failures and keep going
  # later, we'll run these concurrently, but for now we're RAM-limited
  # ignore retcode
  stdout, stderr, retcode = run_shell(["./footprint_lib.py", "--progress",
                                       "--ftpinfo", USERNAME+":"+PASSWORD, url],
                                      silent_ok=True, print_output=False)
  print stdout,
  if stderr and stderr != "":
    print name+":STDERR: ", re.sub(r'\n', '\n'+name+':STDERR: ', stderr)
  if retcode and retcode != 0:
    print name+":RETCODE: "+str(retcode)
  print_progress("load_gbase: done.")

  # TODO: this causes the URL to be downloaded twice-- once for popular
  # words, and once for loading...
  process_popular_words(name, url)


def loaders():
  """put all loaders in one function for easier testing."""
  load_gbase("servenet",
             "http://servenet.org/test/temp/SERVEnetOpportunities001.xml")

  load_gbase("unitedway",
             "http://volunteer.united-e-way.org/"+
             "uwnyc/util/voml/uwnyc-footprint-pull.aspx")
  load_gbase("americansolutions",
             "http://www.americansolutions.com/footprint/footprint.xml")
  load_gbase("meetup", "http://api.meetup.com/footprint?"+
             "key=2c24625a70343bb68451e337e714b22")
  # old custom feed
  #load_gbase("idealist", "http://feeds.idealist.org/xml/feeds/"+
  #           "Idealist-VolunteerOpportunity-VOLUNTEER_OPPORTUNITY_TYPE."+
  #           "en.open.atom.gz")
  load_gbase("extraordinaries", "http://app.beextra.org/opps/list/format/xml")
  load_gbase("idealist", "http://feeds.idealist.org/xml/"+
             "footprint-volunteer-opportunities.xml")
  load_gbase("gspreadsheets",
             "https://spreadsheets.google.com/ccc?key=rOZvK6aIY7HgjO-hSFKrqMw")
  # note: craiglist crawler is run async to this
  load_gbase("craigslist", "craigslist-cache.txt")
  load_gbase("americorps",
             "http://www.americorps.gov/xmlfeed/xml_ac_recruitopps.xml.gz")
  load_gbase("volunteer.gov", "http://www.volunteer.gov/footprint.xml")
  load_gbase("handson",
             "http://archive.handsonnetwork.org/feeds/hot.footprint.xml.gz")

def main():
  """shutup pylint."""
  global USERNAME, PASSWORD
  if len(sys.argv) < 3:
    print "Usage:", sys.argv[0], "<gbase username> <password>"
    sys.exit(1)
  USERNAME = sys.argv[1]
  PASSWORD = sys.argv[2]

  loaders()

  print_progress("final cleanse: keeping only words appearing 10 times")
  for word in KNOWN_WORDS.keys():
    if KNOWN_WORDS[word] < 10:
      del KNOWN_WORDS[word]
  sorted_words = list(KNOWN_WORDS.iteritems())
  sorted_words.sort(cmp=lambda a, b: cmp(b[1], a[1]))

  popfh = open("popular_words.txt", "w")
  for word, freq in sorted_words:
    popfh.write(str(freq)+"\t"+word+"\n")
  popfh.close()
  print_progress("done writing "+POPULAR_WORDS_FN)

if __name__ == "__main__":
  main()
