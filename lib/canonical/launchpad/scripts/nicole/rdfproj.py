#!/usr/bin/python

import string
import urllib2
import os
 
# CONSTANTS
XMLDIR = '/home/freshmeat/'
 
# See http://freshmeat.net/browse/160/ to keep this up to date:
trove_programmingLangs = {
	 163: 'Ada',
	 161: 'APL',
	 184: 'ASP',
	 162: 'Assembly',
	 848: 'Awk',
	 878: 'Basic',
	 164: 'C',
	 892: 'C#',
	 165: 'C++',
	 262: 'Cold Fusion',
	 1028: 'Common Lisp',
	 265: 'Delphi',
	 825: 'Dylan',
	 166: 'Eiffel',
	 869: 'Emacs-Lisp',
	 264: 'Erlang',
	 167: 'Euler',
	 263: 'Euphoria',
	 168: 'Forth',
	 169: 'Fortran',
	 1097: 'Groovy',
	 834: 'Haskell',
	 198: 'Java',
	 816: 'JavaScript',
	 170: 'Lisp',
	 171: 'Logo',
	 1095: 'Lua',
	 172: 'ML',
	 173: 'Modula',
	 258: 'Object Pascal',
	 174: 'Objective C',
	 983: 'OCaml',
	 213: 'Other',
	 817: 'Other Scripting Engines',
	 175: 'Pascal',
	 176: 'Perl',
	 183: 'PHP',
	 985: 'Pike',
	 254: 'PL/SQL',
	 896: 'Pliant',
	 255: 'PROGRESS',
	 177: 'Prolog',
	 178: 'Python',
	 1096: 'REALbasic',
	 179: 'Rexx',
	 835: 'Ruby',
	 242: 'Scheme',
	 180: 'Simula',
	 181: 'Smalltalk',
	 823: 'SQL',
	 182: 'Tcl',
	 185: 'Unix Shell',
	 186: 'Visual Basic',
	 261: 'XBasic',
	 1000: 'YACC',
	 267: 'Zope',
	 }

def getProductSpec(directory, productname):
    filename = productname + '.xml'

    path = os.path.join(directory , filename)
	 
    if not os.access(path, os.F_OK):
        return None

    rdf = open(path).read()
    prod_dict = rdf2dict(rdf)
    prod_dict['product'] = productname
    return prod_dict

def getProjectSpec(projname):
    #rdf = open('fm-projects.rdf').read()
    rdf = open(XMLDIR + projname + '.xml').read()
    #start = rdf.find('<projectname_short>'+projname+'</projectname_short>')
    #start = rdf.rfind('<project>',0,start)
    #end = rdf.find('<project>',start+1)
    #project_rdf = rdf[start:end]
    #del rdf
    #proj_dict = rdf2dict(project_rdf)
    proj_dict = rdf2dict(rdf)
    return proj_dict

def rdf2dict(rdf):
    mydict = {}
    tagdict = {'projectname_full': 'projectname',
               'desc_full': 'description',
               'desc_short': 'description_short',
               'url_homepage': 'homepage',
               'screenshot_thumb': 'screenshot',
               'url_list': 'list',
               'descriminators': 'programminglang',
               'license': 'license',
               'url_tgz': 'url_tgz',
               'url_bz2': 'url_bz2',
               'url_zip': 'url_zip',
               'url_rpm': 'url_rpm',
               'url_deb': 'url_deb',
               'url_osx': 'url_osx',
               'url_bsdport': 'url_bsdport',
               'url_cvs': 'url_cvs',
               }
    for tag in tagdict.keys():
        start = rdf.find('<'+tag+'>')+len('<'+tag+'>')
        end = rdf.find('</'+tag+'>')
        if start <> end:

            if mydict.has_key(tagdict[tag]):

                if type(mydict[tagdict[tag]]) <> type([]):
                    mydict[tagdict[tag]] = [mydict[tagdict[tag]]]

                mydict[tagdict[tag]].append(rdf[start:end])
            else:
                mydict[tagdict[tag]] = rdf[start:end]

    mydict['programminglang'] = extractLangs(mydict['programminglang'])
    #for tag in ['homepage', 'screenshot', 'list']:
    #       if mydict[tag]: mydict[tag] = getUrlRedirect(mydict[tag])
    #for tag in ['list']:
    #       mydict[tag] = [mydict[tag]]
    return mydict

def extractLangs(rdf):
    programminglangs = []
    start = 0
    end = 0
    tag = 'trove_id'
    oldstart = 0
    while start > -1 and start >= oldstart:
        oldstart = start
        start = rdf.find('<'+tag+'>', start+1)+len('<'+tag+'>')
        if start > -1 and start >= end:
            end = rdf.find('</'+tag+'>', start)
            trove_id = int(rdf[start:end])
            if trove_programmingLangs.has_key(int(trove_id)):
                programminglangs.append(trove_programmingLangs[trove_id])
    return programminglangs

def getUrlRedirect(url):
    try:
        urlobj = urllib2.urlopen(url)
    except urllib2.HTTPError:
        return None
    realUrl = urlobj.geturl()
    urlobj.close()
    return realUrl
