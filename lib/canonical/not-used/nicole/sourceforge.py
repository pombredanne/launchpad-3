#!/usr/bin/python

#
# Retrieve product details from sourceforge / freshmeat / savannah.gnu.org
#

## Added by cprov 20041022
#-> use "sv" instead of "savannah.gnu.org", tricky, isn't it ?
#
#-> add to dict the field [self.repository] as product_url
#
# Version 20041021
##############################################################
# Primary way to use this library is using:
#
#       getProductSpec(projname, repository)
#
# Where:
#    projname is a string like 'python', and 
#    repository is either 'sf' for SourceForge, or 'fm' for FreshMeat,
#    or 'savannah.gnu.org' for, err, savannah.gnu.org.
#    NOTE: savannah.gnu.org works for non-GNU products on savannah.nongnu.org as well.
#
# If no repository is passed, the default is 'sf'.
#
# getProductSpec() returns a dictionary with the following keys:
#
# productname: This is the official name of the product (not the unixname).
#              Example: 'Python'
#
# homepage: This is the URL to the home page of the product
#           Example: 'http://www.python.org'
#
# programminglang: This is a list of programming languages used by the product.
#                  If none are found, an empty list will be present.
#                  Example: ['C++','Python']
#
# description: This is a description of the product - a paragraph or two.
#              Example: 'This is the Python programming language...'
#
# list: This is a list of mailing list URLs for the product.
#       * ONLY IMPLEMENTED FOR SOURCEFORGE *
#       Note: This retrieves an additional page from sf.net to get the list URLs
#       Example: ['http://lists.sourceforge.net/mailman/listinfo/mediaportal-cvs']
#
# screenshot: This is the URL of a screenshot of the product.
#             * ONLY IMPLEMENTED FOR FRESHMEAT *
#             Example: 'http://freshmeat.net/screenshots/40861/43540/'
#
# devels: A dictionary of the product's significant developers.
#         For SorceForge, this returns all the *admins* of the product.
#             Note: This retrieves 1 additional page for each admin.
#         For Freshmeat, this returns only the product's author since admins
#         are not defined for all products.
#         The keys are the authors' names, and the values are email addresses.
#         Where possible, email addresses from FreshMeat are de-obfuscated: me (at) domain (dot) com -> me@domain.com
#         Example: {'Morgan Collett':'morgan@mcode.co.za'}
#
# naturallang: This is a list of natural languages that the product supports.
#              * ONLY IMPLEMENTED FOR SOURCEFORGE *
#              Example: ['English','Chinese (Simplified)']
#################################################################

import urllib2
import re
import string

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

# Constants
class Error(Exception):
    pass

#===============================================================
# XXX cprov 2005-01-26: Sanitizer for Upstream ...!!!!
from sgmllib import entityref
from htmlentitydefs import entitydefs

def entities_remove(data):
    # XXX: cprov 2005-01-26:
    # Use some blackmagic to remove HTML pieces.
    mapset = re.findall(entityref, data)
    for key in mapset:
        data = re.sub(entityref, entitydefs[key], data)
    return data
#==============================================================

def getProductSpec(product, repository='sf'):
    page = ProductPage(product, repository)
    #page.makeDict() # --- the ProductPage now does this automatically
    return page.getDict()

def makeURL(product, repository='sf'):
    if repository=='sf':
        url = 'http://sourceforge.net/projects/'+product+'/'
    elif repository=='fm':
        url = 'http://freshmeat.net/projects/'+product+'/'
    elif repository=='sv':
        url = 'http://savannah.gnu.org/projects/'+product+'/'
    else: raise Error, 'invalid repository: '+repository
    return url

def getHTML(url):
    try:
        urlobj = urllib2.urlopen(url)
    except (urllib2.HTTPError, urllib2.URLError):
        return None
    html = urlobj.read()
    urlobj.close()
    return html

def unobfuscate_fm_email(email):
    # Freshmeat obfuscates email addresses using a simple scheme
    # like this: user [at] domain [dot] com, or
    # user __dash__ at __dash__ domain __dash__ dot __dash__ com
    # For all known permutations, the following works:
    delimiters = [[' [', '] '], [' |', '| '], [' (',') '], [' __','__ '],
                  [' __dash__ ',' __dash__ '], [' |dash| ',' |dash| '],
                  [' [dash] ',' [dash] '], [' (dash) ',' (dash) '],
                  ['(', ')'], [' ', ' ']]
    symbols = {'at': '@', 'dot': '.', 'dash': '-', 'AT': '@', 'DOT': '.'}
    for symbol in symbols.keys():
        for delimiter in delimiters:
            email = string.join(string.split(email, delimiter[0]+symbol+delimiter[1]), symbols[symbol])
    # Some exceptions to the above
    email = email.replace('AT(@)', '@')
    email = email.replace('DOT(.)', '.')
    return email

class ProductPage:
    # A possible rewrite of this could be done by making classes 'SFPage' and 'FMPage' (and others for
    # any other repositories) inherit from a generic class, and putting the 'sf' or 'fm' specific code
    # in those classes...
    def __init__(self, product, repository='sf'):
        self.product = product
        # handle alternative names of repositories:
        if repository=='sourceforge' or repository=='sourceforge.net':
            repository = 'sf'
        if repository=='freshmeat' or repository=='freshmeat.net':
            repository = 'fm'
        if repository=='savannah.nongnu.org' or repository=='savanah.gnu.org':
            # Note that savannah.gnu.org redirects to savannah.nongnu.org
            # for non-GNU products
            # but the redirect is handled transparently - we can code for the one case and it still works.
            repository = 'sv'
        self.repository = repository
        self.url = makeURL(self.product, self.repository)
        self.html = getHTML(self.url)
        if self.html == None:
            raise Error, 'Could not retrieve product details - perhaps product not found on '+self.repository
        self.theDict = {}
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            if string.find(self.html, 'Invalid Project') > -1:
                raise Error, 'Product not found on '+self.repository
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            if string.find(self.html, 'The project name you specified could not be found in our database') > -1:
                raise Error, 'Product not found on '+self.repository
        ### SAVANNAH.GNU.ORG ###
        elif self.repository == 'sv':
            if string.find(self.html, '<h3 class="feedbackerror">Invalid group [#1]; </h3><p>That group does not exist.</p>') > -1:
                raise Error, 'Product not found on '+self.repository
        self.soup = BeautifulSoup(self.html)
        self.makeDict()

    def getProductName(self):
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            result = re.search('Project: .*Summary', self.html)
            s = self.html[result.start()+9:result.end()-9]
            return s
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            start = string.find(self.html, '<title>freshmeat.net: Project details for ')
            start = start + 42
            end = string.find(self.html, '</title>', start)
            s = string.strip(self.html[start:end])
            return s
        ### SAVANNAH.GNU.ORG ###
        elif self.repository == 'sv':
            start = string.find(self.html, '<h2 class="toptitle">')
            if start == -1: return None
            start = string.find(self.html, 'class="icon">', start) + 13
            end = string.find(self.html, ' - Summary</h2>', start)
            s = string.strip(self.html[start:end])
            return s
        else:
            return None

    #def getRSSPage(self):
    #    ### SOURCEFORGE ###
    #    if self.repository == 'sf':
    #        start = string.find(self.html, '/export/rss2_project.php?group_id=')
    #        if start == -1: return None
    #        end = string.find(self.html, '">', start)
    #        rssUrl = 'http://sourceforge.net' + self.html[start:end]
    #        self.rsspage = getHTML(rssUrl)
    #        start = string.find(self.rsspage, '<p><b>Project summary (including basic statistics)</b><br />')
    #        if start == -1: return -1 ######### CHANGE TO NONE ############
    #        start = string.find(self.rsspage, '<a href="', start) + 9
    #        end = string.find(self.rsspage, '">', start)
    #        rssSummaryPageUrl = self.rsspage[start:end]
    #        self.rssSummaryPage = getHTML(rssSummaryPageUrl)
    #        return rssSummaryPageUrl
    #        ### WE WOULD WANT TO PARSE THE RSS PAGE HERE ###



    def getDescription(self):
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            start = string.find(self.html, 'Summary</A>')
            if start == -1: return None
            start = string.find(self.html, '<TABLE', start)
            start = string.find(self.html, '<p>', start)
            end = string.find(self.html, '<p>', start+1)
            s = self.html[start+3:end]
            s = string.strip(s)
            s = string.join(string.split(s, '\r\n'), ' ')
            return s
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            start = string.find(self.html, '<b>About:</b>')
            if start == -1: return None
            start = string.find(self.html, '<br>', start)
            end = string.find(self.html, '<p>', start)
            s = self.html[start+4:end]
            s = string.strip(s)
            s = string.join(string.split(s, '\r\n'), ' ')
            return s
        ### SAVANNAH.GNU.ORG ###
        elif self.repository == 'sv':
            start = string.find(self.html, '<tr><td class="indexcenter"><p>')
            if start == -1: return None
            start = string.find(self.html, '<p>', start+31)+3
            end = string.find(self.html, '</p>', start)
            s = self.html[start:end]
            s = string.strip(s)
            s = string.join(string.split(s, '\r\n'), ' ')
            s = string.join(string.split(s, '<br /> '), ' ')
            if s[:64] == 'This project has not yet submitted a short description. You can ':
                return None
            return s
        else:
            return None

    def getHomePage(self):
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            #result = re.search('href.*Home\ Page', self.html)
            #if result == None: return None
            #s = self.html[result.start()+6:result.end()-11]
            #return s
            homePage = None
            a = self.soup('a', {'class': 'tabs'})
            for link in a:
                if link.contents[0] == 'Home Page':
                    homePage = link['href']
            return homePage
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            start = string.find(self.html, 'Homepage:')
            if start == -1: return None
            start = string.find(self.html, 'http://', start)
            end = string.find(self.html, '</a>', start)
            return self.html[start:end]
        ### SAVANNAH.GNU.ORG ###
        elif self.repository == 'sv':
            start = string.find(self.html, '&nbsp;Project Homepage</a></td>')
            if start == -1: return None
            start = string.rfind(self.html, '<a href="', 0, start)
            end = string.find(self.html, '">', start)
            return self.html[start+9:end]
        else:
            return None

    def getProgramminglang(self):
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            result = re.search('Programming\ Language.*BR>', self.html)
            if result == None: return None
            langstring = self.html[result.start()+22:result.end()]
            # Find first BR
            end = string.find(langstring, '<BR>')
            langstring = langstring[:end]
            # split up, remove <A...> tags
            langlist1 = string.split(langstring, ',')
            langlist = []
            for lang in langlist1:
                start = string.find(lang, '>')
                lang = lang[start+1:]
                end = string.find(lang, '<')
                lang = lang[:end]
                langlist.append(lang)
            return langlist
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            start = string.find(self.html, '[Programming Language]')
            if start == -1: return None
            start = string.find(self.html, '<td', start)
            start = string.find(self.html, '<td', start+1)
            end = string.find(self.html, '</td>', start)
            langstring = self.html[start:end]
            langlist1 = string.split(langstring, ',')
            langlist = []
            for lang in langlist1:
                start = string.find(lang, '<small>')
                start = start + 8
                end = string.find(lang, '<', start)
                lang = lang[start:end]
                langlist.append(lang)
            return langlist
        else:
            return None

    def getNaturallang(self):
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            result = re.search('Natural\ Language.*BR>', self.html)
            if result == None: return None
            langstring = self.html[result.start()+22:result.end()]
            # Find first BR
            end = string.find(langstring, '<BR>')
            langstring = langstring[:end]
            # split up, remove <A...> tags
            langlist1 = string.split(langstring, ',')
            langlist = []
            for lang in langlist1:
                start = string.find(lang, '>')
                lang = lang[start+1:]
                end = string.find(lang, '<')
                lang = lang[:end]
                langlist.append(lang)
            return langlist
        else:
            return None

    def getMailinglist(self):
        # Check for mailing list page
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            start = string.find(self.html, '&nbsp;Mailing Lists</A>')
            if start == -1: return None
            start = string.rfind(self.html, '/mail/?', 0, start)
            end = string.find(self.html, '"', start+1)
            listURL = 'http://sourceforge.net' + self.html[start:end]
            # fetch mailing list page
            self.listpage = getHTML(listURL)
            # Extract mailing list URLs
            start = 0
            urls = []
            while start >= 0:
                start = string.find(self.listpage, 'Subscribe/Unsubscribe/Preferences', start+1)
                if start >= 0:
                    urlstart = string.rfind(self.listpage, 'http://lists.sourceforge', 0, start)
                    urlend = start - 2
                    url = self.listpage[urlstart:urlend]
                    urls.append(url)
            # Construct return list
            if urls: return urls
            else: return None
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            #
            # Note: for FreshMeat, this currently only works for projects that point
            # to a sourceforge page for the mailing lists.
            # Other projects point to an arbitrary page somewhere else that
            # cannot be parsed without further information.
            #
            start = string.find(self.html, 'Mailing list archive:</b>')
            if start == -1: return None
            end = string.find(self.html, '</a>', start)
            start = string.find(self.html, 'http://sourceforge.net/mail/', start, end)
            if start == -1: return None
            listURL = self.html[start:end]
            # fetch mailing list page
            self.listpage = getHTML(listURL)
            # Extract mailing list URLs
            start = 0
            urls = []
            while start >= 0:
                start = string.find(self.listpage, 'Subscribe/Unsubscribe/Preferences', start+1)
                if start >= 0:
                    urlstart = string.rfind(self.listpage, 'http://lists.sourceforge', 0, start)
                    urlend = start - 2
                    url = self.listpage[urlstart:urlend]
                    urls.append(url)
            # Construct return list
            if urls: return urls
            else: return None

        else:
            return None

    def getScreenshot(self):
        # only freshmeat has screenshots
        if self.repository == 'sf':
            return None
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            start = string.find(self.html, '<a target="screenshot"')
            if start == -1: return None
            start = string.find(self.html, 'href="/screenshots/', start)
            end = string.find(self.html, '/">', start)
            ssurl = 'http://freshmeat.net' + self.html[start+6:end+1]
            return ssurl
        else: return None

    def getDevels(self):
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            # We can get list of product admins with @sf.net emails
            start = string.find(self.html, 'Project Admins:</SPAN>')
            if start == -1: return None
            end = string.find(self.html, '<SPAN CLASS="develtitle">Developers', start)
            adminhtml = self.html[start:end]
            admins = []
            adminstart = 0
            while adminstart >= 0:
                adminstart = string.find(adminhtml, '<a href="/users/', adminstart + 1)
                if adminstart >= 0:
                    adminend = string.find(adminhtml, '">', adminstart)
                    adminurl = adminhtml[adminstart+16:adminend-1]
                    admins.append(adminurl)
            devels = {}
            for admin in admins:
                adminurl = 'http://sourceforge.net/users/' + admin + '/'
                adminhtml = getHTML(adminurl)
                namestart = string.find(adminhtml, 'Publicly Displayed Name:') + 39
                nameend = string.find(adminhtml, '</B>', namestart)
                name = adminhtml[namestart:nameend]
                email = admin + '@users.sourceforge.net'
                devels[name] = email
            return devels
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            # We can get a single author and obfuscated email address
            start = string.find(self.html, '<b>Author:</b>')
            if start == -1: return None
            start = start + 18
            endname = string.find(self.html, '<a href', start)
            checkForAddrInName = string.find(self.html, '&lt;', start, endname)
            if checkForAddrInName >= 0:
                endname = checkForAddrInName
            name = string.strip(self.html[start:endname])
            emailstart = string.find(self.html, '<a href', start) + 16
            emailend = string.find(self.html, '">', emailstart)
            email = self.html[emailstart:emailend]
            # unobfuscate email address
            email = unobfuscate_fm_email(email)
            return {name: email}
        else: return None

    def getReleases(self):
        ### SOURCEFORGE ###
        if self.repository == 'sf':
            aLinks = self.soup('a')
            fileLinks = []
            for link in aLinks:
                if 'showfiles' in str(link):
                    fileLinks.append(link)

            for link in fileLinks:
                try:
                    if link['class'] == 'tabs':
                        fileLinks.remove(link)
                except: pass
            releases = []
            # now only have the correct a links for the released files
            counter = 0
            for link in fileLinks:
                if counter == 0:
                    releasedFile = str(link.next)
                    version = str(link.next.next.next.next)
                    fileDate = str(link.next.next.next.next.next.next.next)
                    if releasedFile <> '[View ALL Project Files]':
                        releases.append((releasedFile, version, fileDate))
                    counter = counter + 1
                elif counter == 2: counter = 0
                else: counter = counter + 1
            return releases
        ### FRESHMEAT ###
        elif self.repository == 'fm':
            aLinks = self.soup('a')
            fileLinks = []
            for link in aLinks:
                if '/branches/' in str(link):
                    fileLinks.append(link)
            releases = []
            for link in fileLinks:
                releasedFile = str(link.next)
                version = str(link.next.next.next.next.next.next.next)
                fileDate = string.strip(str(link.next.next.next.next.next.next.next.next.next.next.next))
                releases.append((releasedFile, version, fileDate))
            return releases
        else:
            return None

    def makeDict(self):
        self.theDict = {}
        
        self.theDict['product'] = entities_remove(self.product)

        #
        productname = self.getProductName()
        if productname:
            self.theDict['productname'] = entities_remove(productname)
        else:
            self.theDict['productname'] = None
        #
        homepage = self.getHomePage()
        if homepage:
            self.theDict['homepage'] = entities_remove(homepage)
        else:
            self.theDict['homepage'] = None 
        #
        programminglang = self.getProgramminglang()

        if programminglang:
            self.theDict['programminglang'] = programminglang
        else:
            self.theDict['programminglang'] = []
        #
        description = self.getDescription()
        if description:
            self.theDict['description'] = entities_remove(description)
        else:
            self.theDict['description'] = None
        #
        mailinglist = self.getMailinglist()
        if mailinglist:
            self.theDict['list'] = mailinglist
        else:
            self.theDict['list'] = []
        #
        screenshot = self.getScreenshot()
        if screenshot:
            self.theDict['screenshot'] = entities_remove(screenshot)
        else:
            self.theDict['screenshot'] = None 
        #
        devels = self.getDevels()        
        if devels:
            self.theDict['devels'] = devels
        else:
            self.theDict['devels'] = {}
        #
        naturallang = self.getNaturallang()
        if naturallang:
            self.theDict['naturallang'] = entities_remove(naturallang)
        else:
            self.theDict['naturallang'] = None
            
        #
        releases = self.getReleases()
        if releases:
            self.theDict['releases'] = releases
        else:
            self.theDict['releases'] = []

        ## Insert the Product Original 
        self.theDict[self.repository] = entities_remove(self.product)

    def getDict(self):
        return self.theDict

