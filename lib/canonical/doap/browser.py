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

    def update(self):
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
        return DBProject.select(q)


