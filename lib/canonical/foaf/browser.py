# Copyright 2004 Canonical Ltd

from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import TextLine, Int, Choice

from canonical.launchpad.database import Project
from canonical.launchpad.database import Product
from canonical.database import sqlbase

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('foaf')

from canonical.lp import dbschema

from canonical.launchpad.interfaces import *



class FOAFApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def update(self):
        # XXX: do something about this
        '''Handle request and setup this view the way the templates expect it
        '''
        from sqlobject import OR, LIKE, CONTAINSSTRING, AND
        if self.request.form.has_key('query'):
            # TODO: Make this case insensitive
            s = self.request.form['query']
            self.results = Project.select(OR(
                    CONTAINSSTRING(Project.q.name, s),
                    CONTAINSSTRING(Project.q.displayname, s),
                    CONTAINSSTRING(Project.q.title, s),
                    CONTAINSSTRING(Project.q.shortdesc, s),
                    CONTAINSSTRING(Project.q.description, s)
                ))
            self.noresults = not self.results
        else:
            self.noresults = False
            self.results = []

class ProjectContainer(object):
    """A container for Project objects."""

    implements(IProjectContainer)
    table = Project

    def __getitem__(self, name):
        try:
            return self.table.select(self.table.q.name == name)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row

    def search(self, name, title):
        q = '1=1'
        if name:
            q += """ AND name LIKE '%%%%' || %s || '%%%%' """ % (
                    sqlbase.quote(name.lower())
                    )
        if title:
            q += """ AND lower(title) LIKE '%%%%' || %s || '%%%%'""" % (
                    sqlbase.quote(title.lower())
                    )
        return Project.select(q)


