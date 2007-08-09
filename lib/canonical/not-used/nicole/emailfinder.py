#!/usr/bin/python

"""emailfinder.py - add email addresses to xml files

Operate on xml files produced from Freshmeat's fm-projects.rdf,
attempting to get an email address for one of the authors from the
person's page on freshmeat.net - and then update the xml file with
this email address within <author_email> tags.

usage: emailfinder.py [options]

options:
  -h, --help            show this help message and exit
  -f FILE, --file=FILE  Single project XML file
  -l LIST, --list=LIST  List of products
  -d DIR, --dir=DIR     XML directory
  -c CACHE, --cachefile=CACHE
                        Cache file
  -w TIME, --wait=TIME  Interval in seconds

"""

import os
import sys
import time
import string
import pickle
import urllib2
from optparse import OptionParser

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from sourceforge import unobfuscate_fm_email

# Globals
email_cache = {}
email_cache_hits = 0
email_cache_misses = 0
email_file_hits = 0
email_failures = 0
files_processed = 0

def find_email(filename):
    """Read in xml file, get email address from freshmeat.net"""
    global files_processed
    global email_cache_hits
    global email_cache_misses
    global email_file_hits
    global email_failures
    
    try:
        rdf = open(filename).read()
    except IOError:
        print '   FILE NOT FOUND'
        return
    
    files_processed = files_processed + 1

    # if no email continue else break
    an_email = extract_tag(rdf, 'author_email')
    if an_email:
        email_file_hits += 1
        print '   File Hit - already done'
        return

    # Get author page
    for author in extract_tags(rdf, 'author'):
        name = extract_tag(author, 'author_name')
        url = extract_tag(author, 'author_url')
        if not url:
            continue
        if email_cache.has_key(url):
            an_email = email_cache[url]
            email_cache_hits += 1
            print '   (found in cache)',
        else:
            time.sleep(WAIT)
            html = get_html(url)
            email_cache_misses += 1
            # Extract email address
            an_email = get_email(html)
            # Reject email addresses with a space in them
            if an_email and ' ' in an_email:
                print '   BAD EMAIL: ' + an_email
                an_email = None
        if an_email:
            break

    if an_email:
        print '   '+an_email
        email_cache[url] = an_email
        # Add author email address to file text
        current = '<author_url>' + url + '</author_url>'
        proposed = ('<author_url>' + url + '</author_url>\n' +
                    '        <author_email>' +
                    an_email + '</author_email>')
        rdf = rdf.replace(current, proposed)
    
        # update flag <local_status>NEW</local_status>
        rdf = rdf.replace('    <local_status>NEW</local_status>\n','')
        rdf = rdf.replace('  </project>',
                      '    <local_status>NEW</local_status>\n  </project>')
        
        # Write back out to file
        open(filename,'w').write(rdf)

    else:
        email_failures += 1


def extract_tag(rdf, tag):
    """Given tag-soup, extract the text between <tag> and </tag>"""
    taglist = extract_tags(rdf, tag, 1)
    if taglist:
        return taglist[0]
    else:
        return None


def extract_tags(rdf, tag, max_occurrences=None):
    """Extract multiple tags from tag soup/RDF

    Given a piece of tag-soup, extract a list of items
    where each is the text appearing between <tag>...</tag>.

    max_occurrences is the maximum number to return
    - use 0 for unlimited.

    """

    soup = BeautifulStoneSoup(rdf)
    items = soup(tag)
    if max_occurrences is not None:
        items = items[:max_occurrences]
    result = []
    # Convert each item into a string, including nested tags
    # XXX morgs 2005-02-01: Check if this actually needs to be
    # recursively nested?
    for item in items:
        item_str = ''
        for i in item.contents:
            if string.strip(str(i)):
                item_str += str(i)
        result.append(str(item_str))
    return result


def get_html(url):
    """Fetch HTML text of a web page from the given URL"""
    try:
        urlobj = urllib2.urlopen(url)
    except (urllib2.HTTPError, urllib2.URLError):
        return None
    if urlobj is not None:
        html = urlobj.read()
        urlobj.close()
        return html
    else:
        return None


def get_email(html):
    """Extract email address from a Freshmeat.net user page.
    
    Example: <b>Email:</b><br>
    <a>kiko (at) async (dot) com (dot) br</a><p>

    """
    if type(html) <> type('asd'): return None
    start = string.find(html, '<b>Email:</b>')
    if start == -1: return None
    # Find the end of the </a> tag
    end = string.find(html, '</a>', start) + len('</a>')
    if end == -1: return None
    # Get the contents of the <a>...</a>
    soup = BeautifulSoup(html[start:end])
    email = soup('a')[0].contents[0].string
    # unobfuscate email address
    email = unobfuscate_fm_email(email)
    return email

def get_files(options):
    files = []
    if options.filename:
        print 'Processing one file: ' + options.filename
        files.append(options.filename)
    elif options.list:
        # Must have directory too
        if not options.directory:
            print 'Please specify directory as well.'
            sys.exit(1)
        print 'Processing list: ' + options.list
        # Verify the access to the LIST file
        filename = options.list
        if not os.access(filename, os.F_OK):
            print 'List file not found:', LIST
            sys.exit(0)

        products = open(filename).readlines()

        # iter through the lines
        for line in products:
            # Get the first column
            product = line.split()[0] + '.xml'
            path = os.path.join(options.directory, product)
            files.append(path)
    elif options.directory:
        # Process all files in DIR
        print 'Processing directory ' + options.directory
        dirfiles = os.listdir(options.directory)
        for filename in dirfiles:
            if filename.endswith('.xml'):
                path = os.path.join(options.directory, filename)
                files.append(path)
    else:
        pass
    return files


if __name__=='__main__':
    parser = OptionParser()

    parser.add_option("-f", "--file", dest="filename",
                      help="Single project XML file",
                      metavar="FILE")

    parser.add_option("-l", "--list", dest="list",
                      help="List of products",
                      metavar="LIST")

    parser.add_option("-d", "--dir", dest="directory",
                      help="XML directory",
                      metavar="DIR",
                      default="freshmeat")

    parser.add_option("-c", "--cachefile", dest="cache",
                      help="Cache file",
                      metavar="CACHE")

    ## Web search interval avoiding to be blocked by high threshold
    ## of requests reached by second
    parser.add_option("-w", "--wait", dest="wait",
                      help="Interval in seconds",
                      metavar="TIME",
                      default="10")

    (options,args) = parser.parse_args()
    
    DIR = options.directory
    FILE = options.filename
    CACHE = options.cache
    WAIT = int(options.wait)
    LIST = options.list

    if CACHE:
        try:
            cache_file = open(CACHE)
            email_cache = pickle.load(cache_file)
            cache_file.close()
            print 'Cache loaded'
        except IOError:
            email_cache = {}

    for xml_file in get_files(options):
        print xml_file
        path = os.path.join(DIR, xml_file)
        find_email(path)

    if CACHE:
        try:
            cache_file = open(CACHE, 'w')
            pickle.dump(email_cache, cache_file)
            cache_file.close()
            print 'Cache saved'
        except IOError:
            sys.stderr.write('Could not write cache file')
    
    # Print statistics
    print 'Files Processed:', files_processed
    print 'Files already with an email:', email_file_hits
    print 'Failed to find emails:', email_failures
    print 'Cache hits:', email_cache_hits
    print 'Cache misses:', email_cache_misses
    
