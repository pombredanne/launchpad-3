# Copyright 2004 Canonical Ltd
#
# arch-tag: 4863ce15-110a-466d-a1fc-54fa8b17d360

from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import TextLine, Int, Choice

from canonical.database import DBProject
from canonical.database import Product
from canonical.database import sqlbase

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('doap')

from canonical.lp import dbschema

from canonical.interfaces import *



class DOAPApplicationView(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def search(self):
        '''Handle request and setup this view the way the templates expect it
        '''
        from sqlobject import OR, LIKE, CONTAINSSTRING, AND
        if self.request.form.has_key('query'):
            # TODO: Make this case insensitive
            s = self.request.form['query']
            self.results = DBProject.select(OR(
                    CONTAINSSTRING(DBProject.q.name, s),
                    CONTAINSSTRING(DBProject.q.displayname, s),
                    CONTAINSSTRING(DBProject.q.title, s),
                    CONTAINSSTRING(DBProject.q.shortdesc, s),
                    CONTAINSSTRING(DBProject.q.description, s)
                ))
            self.noresults = not self.results
        else:
            self.noresults = False
            self.results = []

class ProjectContainerView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.searchrequested = False
        if 'searchquery' in request.form:
            self.searchrequested = True
        self.results = None

    def searchresults(self):
        """Use searchtext to find the list of Projects that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(request.get('searchtext'))
        return self.results

    def tmp(self):
        '''Handle request and setup this view the way the templates expect it
        '''
        from sqlobject import OR, LIKE, CONTAINSSTRING, AND
        if self.request.form.has_key('searchtext'):
            # TODO: Make this case insensitive
            s = self.request.form['searchtext']
            self.results = DBProject.select(OR(
                    CONTAINSSTRING(DBProject.q.name, s),
                    CONTAINSSTRING(DBProject.q.displayname, s),
                    CONTAINSSTRING(DBProject.q.title, s),
                    CONTAINSSTRING(DBProject.q.shortdesc, s),
                    CONTAINSSTRING(DBProject.q.description, s)
                ))
            self.noresults = not self.results
        else:
            self.noresults = False
            self.results = []


class ProjectContainer(object):
    """A container for Project objects."""

    implements(IProjectContainer)
    table = DBProject

    def __getitem__(self, name):
        try:
            return self.table.select(self.table.q.name == name)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row

    def search(self, searchtext):
        q = """name LIKE '%%%%' || %s || '%%%%' """ % (
                sqlbase.quote(searchtext.lower())
                )
        q += """ OR lower(title) LIKE '%%%%' || %s || '%%%%'""" % (
                sqlbase.quote(searchtext.lower())
                )
        q += """ OR lower(shortdesc) LIKE '%%%%' || %s || '%%%%'""" % (
                sqlbase.quote(searchtext.lower())
                )
        q += """ OR lower(description) LIKE '%%%%' || %s || '%%%%'""" % (
                sqlbase.quote(searchtext.lower())
                )
        return DBProject.select(q)


