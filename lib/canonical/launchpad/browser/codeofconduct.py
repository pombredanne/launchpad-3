"""
Zope View Classes to handle Signed Code of Conducts.
Copyright 2004 Canonical Ltd.  All rights reserved.
"""

__metaclass__ = type

# zope imports
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent
from zope.component import getUtility
import zope.security.interfaces

# lp imports
from canonical.lp import dbschema                       
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

# interface import
from canonical.launchpad.interfaces import IPerson, ILaunchBag,\
                                           ICodeOfConduct,\
                                           ISignedCodeOfConductSet

# sqlobject/sqlos
from sqlobject import LIKE, AND


# XXX: cprov 20050224
# Avoid the use of Content classes here !
from canonical.launchpad.database import SignedCodeOfConduct


class SignedCodeOfConductAddView(AddView):
    """Add a new SignedCodeOfConduct Entry."""

    __used_for__ = ICodeOfConduct

    ow = CustomWidgetFactory(ObjectWidget, SignedCodeOfConduct)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        """Verify and Add SignedCoC entry"""
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized(
                "Need an authenticated SignedCoC owner")
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value
        kw['person'] = owner.id

        # use utility to store it in the database
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        sCoC_util.verifyAndStore(**kw)

    def nextURL(self):
        return self._nextURL

    
class SignedCodeOfConductAdminView(object):
    """Admin Console for SignedCodeOfConduct Entries."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)
        self.results = None
        
    def search(self):
        """Search Signed CoC by Owner Displayname"""
        name = self.request.form.get('name')
        searchfor = self.request.form.get('searchfor')

        if name:
            # use utility to query on SignedCoCs
            sCoC_util = getUtility(ISignedCodeOfConductSet)
            self.results = sCoC_util.searchByDisplayname(name,
                                                         searchfor=searchfor)
            return True

        
