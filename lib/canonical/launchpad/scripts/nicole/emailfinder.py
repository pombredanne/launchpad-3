#!/usr/bin/python

"""Operate on xml files produced from Freshmeat's
fm-projects.rdf, attempting to get an email address
for one of the authors from the person's page
on freshmeat.net - and then update the xml file
with this email address within <author_email> tags."""

import os
import sys
import time
import string
import pickle
import urllib2
from optparse import OptionParser

from sourceforge import unobfuscate_fm_email

# Globals
email_cache = {}
email_cache_hits = 0
email_cache_misses = 0
email_file_hits = 0
email_failures = 0
files_processed = 0

def find_email(filename):
    """Read in xml file for product. If no email for author, fetch it
    from freshmeat.net/projects/<product> and update the file."""

    global files_processed
    global email_cache_hits
    global email_cache_misses
    global email_file_hits
    global email_failures
    
    rdf = open(filename).read()
    files_processed = files_processed + 1

    # if no email continue else break
    an_email = extract_tag(rdf, 'author_email')
    if an_email:
        email_file_hits = email_file_hits + 1
        print '   File Hit - already done'
        return

    # Get author page
    for author in extract_tags(rdf, 'author'):
        name = extract_tag(author, 'author_name')
        url = extract_tag(author, 'author_url')
        if url == None: continue
        if email_cache.has_key(url):
            an_email = email_cache[url]
            email_cache_hits = email_cache_hits + 1
            print '   (found in cache)',
        else:
            time.sleep(WAIT)
            html = get_html(url)
            email_cache_misses = email_cache_misses + 1
            # Extract email address
            an_email = get_email(html)
            # Quick sanity check - throw away if we can't use
            if an_email and ' ' in an_email:
                print '   BAD EMAIL: ' + an_email
                an_email = None
        if an_email:
            break

    if an_email:
        print '   '+an_email
        email_cache[url] = an_email
        # update file with devel
        rdf = rdf.replace('<author_url>'+url+'</author_url>',
                          '<author_url>'+url+'</author_url>\n        <author_email>'
                          +an_email+'</author_email>')
    
        # update flag <local_status>NEW</local_status>
        rdf = rdf.replace('    <local_status>NEW</local_status>\n','')
        rdf = rdf.replace('  </project>',
                      '    <local_status>NEW</local_status>\n  </project>')
        
        # Write back out to file
        open(filename,'w').write(rdf)

    else:
        email_failures = email_failures + 1


def extract_tag(rdf, tag):
    """Given a piece of tag-soup, extract the text between
    <tag> and </tag>"""
    start = rdf.find('<'+tag+'>')
    if start == -1: return
    start = start + len('<'+tag+'>')
    end = rdf.find('</'+tag+'>', start)
    if end == -1: return   # We don't handle unbalanced tags
    return rdf[start:end]


def extract_tags(rdf, tag):
    """Given a piece of tag-soup, extract a list of items
    where each is the text appearing between one of multiple
    <tag>...</tag>"""
    start = 0
    end = 0
    result = []
    while start > -1:
        start = rdf.find('<'+tag+'>', end)
        if start == -1:
            break
        start = start + len('<'+tag+'>')
        end = rdf.find('</'+tag+'>', start)
        if end == -1: break   # We don't handle unbalanced tags
        result.append(rdf[start:end])
    return result


def get_html(url):
    """Fetch URL of a web page"""
    try:
        urlobj = urllib2.urlopen(url)
    except (urllib2.HTTPError, urllib2.URLError):
        return None
    html = urlobj.read()
    urlobj.close()
    return html


def get_email(html):
    """Extract email address from a Freshmeat.net
    user page.
    Example: <b>Email:</b><br>
    <a>kiko (at) async (dot) com (dot) br</a><p>"""
    if type(html) <> type('asd'): return None
    start = string.find(html, '<b>Email:</b>')
    if start == -1: return None
    start = start + 22
    end = string.find(html, '</a>', start)
    if end == -1: return None
    email = html[start:end]
    # unobfuscate email address
    email = unobfuscate_fm_email(email)
    return email


if __name__=='__main__':
    parser = OptionParser()

    parser.add_option("-f", "--file", dest="filename",
                      help="Single project XML file",
                      metavar="FILE")

    parser.add_option("-d", "--dir", dest="directory",
                      help="XML directory",
                      metavar="DIR",
                      default="freshmeat")

    parser.add_option("-c", "--cachefile", dest="cache",
                      help="Cache file",
                      metavar="CACHE")

    ## Web search interval avoiding to be blocked by high threshould
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

    if CACHE:
        try:
            cache_file = open(CACHE)
            email_cache = pickle.load(cache_file)
            cache_file.close()
            print 'Cache loaded'
        except:
            email_cache = {}

    if FILE:
        print 'Processing one file: '+FILE
        xml_file = FILE
        find_email(xml_file)
    else:
        # Process all files in DIR
        print 'Processing directory '+DIR
        files = os.listdir(DIR)
        for xml_file in files:
            if xml_file[-4:] == '.xml':
                print xml_file
                find_email(DIR+'/'+xml_file)
    if CACHE:
        try:
            cache_file = open(CACHE, 'w')
            pickle.dump(email_cache, cache_file)
            cache_file.close()
            print 'Cache saved'
        except:
            sys.stderr.write('Could not write cache file')
    
    # Print statistics
    print 'Files Processed:', files_processed
    print 'Files already with an email:', email_file_hits
    print 'Failed to find emails:', email_failures
    print 'Cache hits:', email_cache_hits
    print 'Cache misses:', email_cache_misses
    
