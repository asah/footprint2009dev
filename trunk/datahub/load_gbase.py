#!/usr/bin/env python
#

"""script for loading into googlebase.
Usage: load_gbase.py username password
"""

import sys
import re
import logging
import subprocess
from datetime import datetime

USERNAME = ""
PASSWORD = ""

LOGPATH = "/home/footprint/public_html/datahub/dashboard/"
LOG_FN = LOGPATH + "load_gbase.log"
DETAILED_LOG_FN = LOGPATH + "load_gbase_detail.log"

def append_log(outstr):
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
  print str(datetime.now())+": loading", name, "from", url
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
  print str(datetime.now())+": load_gbase: done."

def main():
  """shutup pylint."""
  global USERNAME, PASSWORD
  if len(sys.argv) < 3:
    print "Usage:", sys.argv[0], "<gbase username> <password>"
    sys.exit(1)
  USERNAME = sys.argv[1]
  PASSWORD = sys.argv[2]
  # TODO: run craigslist crawler
  load_gbase("gspreadsheets",
             "https://spreadsheets.google.com/ccc?key=rOZvK6aIY7HgjO-hSFKrqMw")
  load_gbase("extraordinaries", "http://app.beextra.org/opps/list/format/xml")
  load_gbase("craigslist", "craigslist-cache.txt")
  load_gbase("americorps",
             "http://www.americorps.gov/xmlfeed/xml_ac_recruitopps.xml.gz")
  load_gbase("volunteer.gov", "http://www.volunteer.gov/footprint.xml")
  load_gbase("handson",
             "http://archive.handsonnetwork.org/feeds/hot.footprint.xml.gz")
  load_gbase("idealist", "http://feeds.idealist.org/xml/feeds/"+
             "Idealist-VolunteerOpportunity-VOLUNTEER_OPPORTUNITY_TYPE."+
             "en.open.atom.gz")
if __name__ == "__main__":
  main()
