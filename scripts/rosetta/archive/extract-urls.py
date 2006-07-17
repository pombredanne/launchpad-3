#!/usr/bin/python

import sre
import sys

pattern = r'<page[^>]*template="([^"]+)"[^>]*lp:url="([^"]+)"[^>]*/>'

def extract_urls(s):
    return [ (url, template) for (template, url) in sre.findall(pattern, s) ]

def main():
    urls = extract_urls(sys.stdin.read())
    urls.sort()

    for url, template in urls:
        print "%s\n\t%s\n" % (url, template)

if __name__ == '__main__':
    main()

