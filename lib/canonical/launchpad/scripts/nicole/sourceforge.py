#!/usr/bin/python

#
# Retrieve project details from sourceforge / freshmeat
#

# Version 20041004

##############################################################
# Primary way to use this library is using:
#
#       getProjectSpec(projname, repository)
#
# Where:
#    projname is a string like 'python', and 
#    repository is either 'sf' for SourceForge, or 'fm' for FreshMeat.
#
# If no repository is passed, the default is 'sf'.
#
# getProjectSpec() returns a dictionary with the following keys:
#
# projectname: This is the official name of the project (not the unixname).
#              Example: 'Python'
#
# homepage: This is the URL to the home page of the project
#           Example: 'http://www.python.org'
#
# programminglang: This is a list of programming languages used by the project.
#                  If none are found, an empty list will be present.
#                  Example: ['C++','Python']
#
# description: This is a description of the project - a paragraph or two.
#              Example: 'This is the Python programming language...'
#
# list: This is a list of mailing list URLs for the project.
#       * ONLY IMPLEMENTED FOR SOURCEFORGE *
#       Note: This retrieves an additional page from sf.net to get the list URLs.
#       Example: ['http://lists.sourceforge.net/mailman/listinfo/mediaportal-cvs']
#
# screenshot: This is the URL of a screenshot of the project.
#             * ONLY IMPLEMENTED FOR FRESHMEAT *
#             Example: 'http://freshmeat.net/screenshots/40861/43540/'
#
# devels: A dictionary of the project's significant developers.
#         For SorceForge, this returns all the *admins* of the project.
#             Note: This retrieves 1 additional page for each admin.
#         For Freshmeat, this returns only the project's author since admins are not defined for all projects.
#         The keys are the authors' names, and the values are email addresses.
#         Where possible, email addresses from FreshMeat are de-obfuscated: me (at) domain (dot) com -> me@domain.com
#         Example: {'Morgan Collett':'morgan@mcode.co.za'}
#
# naturallang: This is a list of natural languages that the project supports.
#              * ONLY IMPLEMENTED FOR SOURCEFORGE *
#              Example: ['English','Chinese (Simplified)']
#################################################################

import urllib2
import re
import string

# Constants
Error = 'sourceforge.py error'

def getProjectSpec(project, repository='sf'):
	page = ProjectPage(project, repository)
	#page.makeDict() # --- the ProjectPage now does this automatically
	return page.getDict()

def makeURL(project, repository='sf'):
	if repository=='sf':
		url = 'http://sourceforge.net/projects/'+project+'/'
	elif repository=='fm':
		url = 'http://freshmeat.net/projects/'+project+'/'
	else: raise Error, 'invalid repository: '+repository
	return url

def getHTML(url):
	try: urlobj = urllib2.urlopen(url)
	except urllib2.HTTPError: return None
	html = urlobj.read()
	urlobj.close()
	return html

def unobfuscate_fm_email(email):
	# Freshmeat obfuscates email addresses using a simple scheme
	# like this: user [at] domain [dot] com, or user __dash__ at __dash__ domain __dash__ dot __dash__ com
	# For all known permutations, the following works:
	delimiters = [[' [', '] '], [' |', '| '], [' (',') '], [' __','__ '], [' __dash__ ',' __dash__ '], [' |dash| ',' |dash| '], [' [dash] ',' [dash] '], [' (dash) ',' (dash) ']]
	symbols = {'at': '@', 'dot': '.'}
	for symbol in symbols.keys():
		for delimiter in delimiters:
			email = string.join(string.split(email, delimiter[0]+symbol+delimiter[1]), symbols[symbol])
	return email

class ProjectPage:
	# A possible rewrite of this could be done by making classes 'SFPage' and 'FMPage' (and others for
	# any other repositories) inherit from a generic class, and putting the 'sf' or 'fm' specific code
	# in those classes...
	def __init__(self, project, repository='sf'):
		self.project = project
		self.repository = repository
		self.url = makeURL(self.project, self.repository)
		self.html = getHTML(self.url)
		if self.html == None: raise Error, 'Could not retrieve project details - perhaps project not found on '+self.repository
		self.theDict = {}
		if self.repository == 'sf':
			if string.find(self.html, 'Invalid Project') > -1:
				raise Error, 'Project not found on '+self.repository
		elif self.repository == 'fm':
			if string.find(self.html, 'The project name you specified could not be found in our database') > -1:
				raise Error, 'Project not found on '+self.repository
		self.makeDict()

	def getProjectName(self):
		if self.repository == 'sf':
			result = re.search('Project: .*Summary', self.html)
			s = self.html[result.start()+9:result.end()-9]
			return s
		elif self.repository == 'fm':
			start = string.find(self.html, '<title>freshmeat.net: Project details for ')
			start = start + 42
			end = string.find(self.html, '</title>', start)
			s = string.strip(self.html[start:end])
			return s
		else:
			return None


	def getDescription(self):
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
		elif self.repository == 'fm':
			start = string.find(self.html, '<b>About:</b>')
			if start == -1: return None
			start = string.find(self.html, '<br>', start)
			end = string.find(self.html, '<p>', start)
			s = self.html[start+4:end]
			s = string.strip(s)
			s = string.join(string.split(s, '\r\n'), ' ')
			return s
		else:
			return None

	def getHomePage(self):
		if self.repository == 'sf':
			result = re.search('href.*Home\ Page', self.html)
			if result == None: return None
			s = self.html[result.start()+6:result.end()-11]
			return s
		elif self.repository == 'fm':
			start = string.find(self.html, 'Homepage:')
			if start == -1: return None
			start = string.find(self.html, 'http://', start)
			end = string.find(self.html, '</a>', start)
			return self.html[start:end]
		else:
			return None

	def getProgramminglang(self):
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
		elif self.repository == 'fm':
			return None
		else:
			return None

	def getMailinglist(self):
		# Check for mailing list page
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
		elif self.repository == 'fm':
			start = string.find(self.html, '<a target="screenshot"')
			if start == -1: return None
			start = string.find(self.html, 'href="/screenshots/', start)
			end = string.find(self.html, '/">', start)
			ssurl = 'http://freshmeat.net' + self.html[start+6:end+1]
			return ssurl
		else: return None

	def getDevels(self):
		if self.repository == 'sf':
			# We can get list of project admins with @sf.net emails
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


	def makeDict(self):
		self.theDict = {}
		self.theDict['project'] = self.project
		#
		projectname = self.getProjectName()
		if projectname: self.theDict['projectname'] = projectname
		#
		homepage = self.getHomePage()
		if homepage: self.theDict['homepage'] = homepage
		#
		programminglang = self.getProgramminglang()
		if programminglang: self.theDict['programminglang'] = programminglang
		else: self.theDict['programminglang'] = []
		#
		description = self.getDescription()
		if description: self.theDict['description'] = description
		#
		mailinglist = self.getMailinglist()
		if mailinglist: self.theDict['list'] = mailinglist
		else: self.theDict['list'] = []
		#
		screenshot = self.getScreenshot()
		if screenshot: self.theDict['screenshot'] = screenshot
		#
		devels = self.getDevels()
		if devels: self.theDict['devels'] = devels
		else: self.theDict['devels'] = {}
		#
		naturallang = self.getNaturallang()
		if naturallang: self.theDict['naturallang'] = naturallang

		if self.repository == 'sf':
			self.theDict['sf'] = self.url
			self.theDict['fm'] = None
		if self.repository == 'fm':
			self.theDict['sf'] = None
			self.theDict['fm'] = self.url
		
	def getDict(self):
		return self.theDict

