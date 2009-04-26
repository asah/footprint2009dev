#!/usr/bin/env python
#

"""script for loading into googlebase.
Usage: load_gbase.py username password
"""

import sys
import logging
import subprocess
import datetime

USERNAME = ""
PASSWORD = ""

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
  return output, proc.returncode


def run_shell(command, silent_ok=False, universal_newlines=True,
             print_output=False):
  """run a shell command."""
  data, retcode = run_shell_with_retcode(command, print_output,
                                         universal_newlines)
  #TODO: handle errors
  #if retcode:
  #  error_exit("Got error status from %s:\n%s" % (command, data))
  if not silent_ok and not data:
    error_exit("No output from %s" % command)
  return data

def load_gbase(name, url):
  """shutup pylint."""
  print datetime.now(), "loading", name, "from", url
  run_shell(["./footprint_lib.py", "--ftpinfo", USERNAME+":"+PASSWORD, url],
           silent_ok=True)
  print datetime.now(), "done."

def main():
  """shutup pylint."""
  global USERNAME, PASSWORD
  if len(sys.argv) < 3:
    print "Usage:", sys.argv[0], "<gbase username> <password>"
    sys.exit(1)
  USERNAME = sys.argv[1]
  PASSWORD = sys.argv[2]
  load_gbase("extraordinaries", "http://whichoneis.com/opps/list/format/xml")
  load_gbase("americorps",
             "http://www.americorps.gov/xmlfeed/xml_ac_recruitopps.xml.gz")
  load_gbase("volunteer.gov", "http://www.volunteer.gov/footprint.xml")
  load_gbase("handson",
             "http://archive.handsonnetwork.org/feeds/hot.footprint.xml.gz")
  # TODO: run craigslist crawler
  load_gbase("craigslist", "craigslist-cache.txt")
  load_gbase("idealist", "http://feeds.idealist.org/xml/feeds/"+
             "Idealist-VolunteerOpportunity-VOLUNTEER_OPPORTUNITY_TYPE."+
             "en.open.atom.gz")

if __name__ == "__main__":
  main()
