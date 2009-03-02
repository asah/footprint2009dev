#!/usr/bin/python
#

# TODO: remove silly dependency on dapper.net-- thought I'd need
# it for the full scrape, but ended up not going that way.

from xml.dom import minidom
import urllib
import re
import thread
import time
import datetime

METROS_FN = "craigslist-metros.txt"
CACHE_FN = "craigslist-cache.txt"
pages = {}
page_lock = thread.allocate_lock()
crawlers = 0
crawlers_lock = thread.allocate_lock()
cachefile_lock = thread.allocate_lock()

MAX_CRAWLERS = 10

def read_metros():
  global metros
  metros = {}
  fh = open(METROS_FN, "r")
  for line in fh:
    url,name = line.split("|")
    metros[url] = name

def crawl_metros():
  #<geo dataType="RawString" fieldName="geo" href="http://waterloo.craigslist.org/" originalElement="a" type="field">waterloo / cedar falls</geo>
  print "getting toplevel geos..."
  fh = urllib.urlopen("http://www.dapper.net/RunDapp?dappName=craigslistmetros&v=1&applyToUrl=http%3A%2F%2Fgeo.craigslist.org%2Fiso%2Fus")
  geostr = fh.read()
  fh.close()
  dom = minidom.parseString(geostr)
  nodes = dom.getElementsByTagName("geo")
  
  outfh = open(METROS_FN, "w+")
  domains = []
  for node in nodes:
    domain = node.getAttribute("href")
    #print "finding submetros within", domain
    fh1 = urllib.urlopen(domain)
    domain_homepage = fh1.read()  
    fh1.close()  
  
    #<td align="center" colspan="5" id="topban">
    #<div>
    #<h2>new york city</h2>&nbsp;<sup><a href="http://en.wikipedia.org/wiki/New_York_City">w</a></sup>
    #<span class="for"><a href="/mnh/" title="manhattan">mnh</a>&nbsp;<a href="/brk/" title="brooklyn">brk</a>&nbsp;<a href="/que/" title="queens">que</a>&nbsp;<a href="/brx/" title="bronx">brx</a>&nbsp;<a href="/stn/" title="staten island">stn</a>&nbsp;<a href="/jsy/" title="new jersey">jsy</a>&nbsp;<a href="/lgi/" title="long island">lgi</a>&nbsp;<a href="/wch/" title="westchester">wch</a>&nbsp;<a href="/fct/" title="fairfield">fct</a>&nbsp;</span>
    #</div>
    #</td>
    topbanstrs = re.findall(r'<td align="center" colspan="5" id="topban">.+?</td>', domain_homepage, re.DOTALL)
    for topbanstr in topbanstrs:
      links = re.findall(r'<a href="/(.+?)".+?title="(.+?)".+?</a>', topbanstr, re.DOTALL)
      if len(links) > 0:
        for link in links:
          print domain+link[0],":",link[1]
          outfh.write(domain+link[0]+"|"+link[1]+"\n")
      else:
        names = re.findall(r'<h2>(.+?)</h2>', domain_homepage, re.DOTALL)
        print domain,":",names[0]
        outfh.write(domain+"|"+names[0]+"\n")
  outfh.close()


def crawl(url, ignore):
  global crawlers, crawlers_lock, pages, page_lock, MAX_CRAWLERS

  if url in pages:
      return

  while crawlers > MAX_CRAWLERS:
      time.sleep(1)

  # we don't care if several wake at once
  crawlers_lock.acquire()
  crawlers = crawlers + 1
  crawlers_lock.release()

  proxied_url = "http://www.gmodules.com/ig/proxy//"+url

  page = ""
  attempts = 0
  while attempts < 3 and page == "":
      try:
          fh = urllib.urlopen(proxied_url)
          page = fh.read()
          fh.close()
      except:
          page = ""   # in case close() threw exception
          attempts = attempts + 1
          print "open failed, retry after",attempts,"attempts"
          time.sleep(1)

  if attempts >= 3:
      print "crawl failed after 3 attempts:",url

  if re.search(r'This IP has been automatically blocked', page):
      print "uh oh: craiglist is blocking us.  exiting..."
      exit

  page_lock.acquire()
  pages[url] = page
  page_lock.release()

  cached_page = re.sub(r'\r?\n',' ',page)
  cachefile_lock.acquire()
  outfh = open(CACHE_FN, "a")
  outfh.write(url+"\t"+cached_page+"\n")
  outfh.close()
  cachefile_lock.release()

  crawlers_lock.acquire()
  crawlers = crawlers - 1
  crawlers_lock.release()

def wait_for_page(url):
  res = ""
  while res == "":
      page_lock.acquire()
      if url in pages:
          res = pages[url]
      page_lock.release()
      if res == "":
          time.sleep(2)
  return res

def sync_fetch(url):
    id = thread.start_new_thread(crawl, (url,"foo"))
    return wait_for_page(url)

progstart = time.time()
def secs_since_progstart():
    global progstart
    return time.time() - progstart

def crawl_metro_page(urlbase, indexstr):
  global crawlers, crawlers_lock, pages, page_lock
  url = urlbase + indexstr
  listingpage = sync_fetch(url)
  listingurls = re.findall(r'<p><a href="/(.+?)">', listingpage)
  for listing_url in listingurls:
      #print "found",listing_url,"in",url
      id = thread.start_new_thread(crawl, (urlbase+listing_url, "foo"))
  nextpages = re.findall(r'<a href="(index[0-9]+[.]html)">', listingpage)
  for nextpage_url in nextpages:
      id = thread.start_new_thread(crawl_metro_page, (urlbase+nextpage_url, "foo"))

def load_cache(listings_only):
  global pages
  print "loading cache..."
  try:
      fh = open(CACHE_FN, "r")
      for line in fh:
          res = re.findall(r'(.+?)\t(.+)', line)
          url,page = res[0][0], res[0][1]
          if not listings_only or re.search(r'html$', url):
              pages[url] = page
      fh.close()
  except:
      pass
  num_cached_pages = len(pages)
  print "loaded",num_cached_pages,"pages."

from optparse import OptionParser
if __name__ == "__main__":
  sys = __import__('sys')
  parser = OptionParser("usage: %prog [options]...")
  parser.set_defaults(metros=False)
  parser.add_option("--metros", action="store_true", dest="metros")
  (options, args) = parser.parse_args(sys.argv[1:])
  if options.metros:
    crawl_metros()
  read_metros()
  load_cache(False)

  outstr = ""
  for url in metros:
    thread.start_new_thread(crawl_metro_page, (url, "vol/"))

  time.sleep(1)
  while crawlers > 0:
      while crawlers > 0:
          crawled_pages = len(pages) - num_cached_pages
          pages_per_sec = int(crawled_pages/secs_since_progstart())
          print str(secs_since_progstart())+": main thread: waiting for",crawlers,"crawlers.",
          print crawled_pages,"pages crawled so far ("+str(pages_per_sec)+" pages/sec). ",
          print len(pages),"total pages."
          time.sleep(2)
      # avoid race condition-- give it another 2secs to spawn more threads...
      time.sleep(2)
  exit
