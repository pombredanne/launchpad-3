#!/usr/bin/python

import os
import sys

class getwebdir (object) :
    def __init__ (self, url) :
        self.url = url
        self.rawlist = self.download()

    def glob (self, glob, nodirs = 0) :
        import fnmatch

        matches = []

        for afile in self.rawlist : 

            if (afile[-1:] == "/") :
                lastslash = afile.rfind("/", 0, -1)
            else :
                lastslash = afile.rfind("/")

            if (fnmatch.fnmatch(afile[lastslash + 1:], glob)) :
                if (nodirs and afile[-1:] == "/") :
                    continue
                matches.append(afile);

        return matches


    def download(self) :
        
        import httplib

        (scheme, host, path, query, fragment) = httplib.urlsplit(self.url)

        scheme = scheme.lower()

        if scheme == 'http' :
            filelist = self.listhttp()
        elif scheme == 'ftp' :
            filelist = self.listftp()
        else :
            raise "Unsupported scheme %" % scheme

        return filelist

    def listhttp(self) :
        import httplib
        from BeautifulSoup import BeautifulSoup


        (scheme, host, path, query, fragment) = httplib.urlsplit(self.url)

        session = httplib.HTTP(host)
        
        session.putrequest ('GET', path)
        session.putheader ('Host', host)
        session.endheaders()
        
        code = session.getreply()
        
        if ( code[0] == 200 ) :
            fromweb = session.getfile().read()
        else :
            raise DownloadUnsuccessfullError("Unable to download requested file")


        websoup = BeautifulSoup()
        websoup.feed(fromweb)

        filelist = []

        for ahref in websoup("a") :
            url = ahref.get("href")
            filelist.append("http://" + host + path + url)

        return filelist


    def listftp(self) :
        import httplib
        from ftplib import FTP

        (scheme, host, path, query, fragment) = httplib.urlsplit(self.url)

        session = FTP(host)
        session.login()

        session.cwd(path)

        answer = session.nlst()

        filelist = []
        for direntry in answer :
            anentry = "ftp://" + host + path + direntry
            filelist.append(anentry)

        return filelist


