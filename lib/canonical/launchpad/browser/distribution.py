
# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import implements
from zope.schema import TextLine, Int, Choice

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent

from canonical.launchpad.database import Distribution, DistributionSet

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.interfaces import IDistribution, \
        IDistributionSet, IPerson

from zope.app.form.browser.add import AddView
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.form import CustomWidgetFactory

import zope.security.interfaces


class DistributionView:

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-distro-actions.pt')

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-distro-details.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    

class DistributionSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def count(self):
        return self.context.count()


class DistributionSetAddView(AddView):

    __used_for__ = IDistributionSet

    ow = CustomWidgetFactory(ObjectWidget, Distribution)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the product
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized, "Need an authenticated owner"
        kw = {}
        for item in data.items():
            kw[str(item[0])] = item[1]
        kw['owner'] = owner
        distribution = Distribution(**kw)
        notify(ObjectCreatedEvent(distribution))
        self._nextURL = kw['name']
        return distribution

    def nextURL(self):
        return self._nextURL


    def add_action(self):
        title = self.request.get("title", "")
        description = self.request.get("description", "")
        domain = self.request.get("domain", "")
        person = IPerson(self.request.principal, None)

        
        if not person:
            return False
        
        if not title:
            return False

        dt = getUtility(IDistroTools)
        res = dt.createDistro(person.id, name, displayname,
            title, summary, description, domain)
        self.results = res
        return res

class DistributionSetSearchView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form  = request.form

    def results(self):
        return []

    def search_action(self):
        return True

    def count(self):
        return 3
