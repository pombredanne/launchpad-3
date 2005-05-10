# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent
from zope.component import getUtility
import zope.security.interfaces

from sqlobject.sqlbuilder import AND, IN, ISNULL

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.database.sqlbase import quote

from canonical.launchpad.interfaces import IPackaging, IPackagingUtil

class PackagingAddView(AddView):

    __used_for__ = IPackaging
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # retrieve submitted values from the form
        productseries = data['productseries']
        sourcepackagename = data['sourcepackagename']
        distrorelease = data['distrorelease']
        packaging = data['packaging']
        
        # Invoke utility to create a packaging entry
        util = getUtility(IPackagingUtil)
        util.createPackaging(productseries, sourcepackagename,
                             distrorelease, packaging)

        # back to Product Page 
        self._nextURL = '.'

    def nextURL(self):
        return self._nextURL

