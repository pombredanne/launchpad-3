"""
Zope View Classes to handle Signed Code of Conducts.
Copyright 2004 Canonical Ltd.  All rights reserved.
"""

__metaclass__ = type

# zope imports
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.form.browser.add import AddView, EditView
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
                                           ISignedCodeOfConduct,\
                                           ISignedCodeOfConductSet


# python
from datetime import datetime

# XXX: cprov 20050224
# Avoid the use of Content classes here !
from canonical.launchpad.database import SignedCodeOfConduct


class CodeOfConductView(object):
    """Simple view class for CoC page."""
    
    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-codeofconduct-actions.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

class CodeOfConductSetView(object):
    """Simple view class for CoCSet page."""
    
    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-codeofconductset-actions.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request


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


class SignedCodeOfConductAckView(AddView):
    """Acknowledge a Paper Submitted CoC."""

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
        """Verify and Add the Acknowledge SignedCoC entry."""
        kw = {}
        
        for key, value in data.items():
            kw[str(key)] = value
            
        recipient = IPerson(self.request.principal, None)
        kw['recipient'] = recipient.id
        
        # use utility to store it in the database
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        sCoC_util.acknowledgeSignature(**kw)

    def nextURL(self):
        return self._nextURL


class SignedCodeOfConductView(object):
    """Simple view class for SignedCoC page."""
    
    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-signedcodeofconduct-actions.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    
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
            # XXX: cprov 20050226
            # force None when no row was found
            # is it an SQLObject bug ?
            if self.results.count() == 0:
                self.results = None

            return True

        
class SignedCodeOfConductEditView(EditView):
    """Edit a SignedCodeOfConduct Entry.
    When edited:
     * set new datecreated,
     * clear recipient,
     * clear admincomment,
     * clear active.
    """

    __used_for__ = ISignedCodeOfConduct

    ow = CustomWidgetFactory(ObjectWidget, SignedCodeOfConduct)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw

    def __init__(self, context, request):
        self.context = context
        self.request = request
        EditView.__init__(self, context, request)

    def changed(self):
        self.context.datecreated = datetime.utcnow()
        self.context.recipient = None
        self.context.admincomment = None
        self.context.active = None
        # now redirect to view the SignedCoC
        self.request.response.redirect(self.request.URL[-1])


class SignedCodeOfConductActiveView(EditView):
    """Active a SignedCodeOfConduct Entry.
    When activating a signature:
     * Grant a new admincomment,
     * store the recipient,
     * set active.
    """

    __used_for__ = ISignedCodeOfConduct

    ow = CustomWidgetFactory(ObjectWidget, SignedCodeOfConduct)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw

    def __init__(self, context, request):
        self.context = context
        self.request = request
        EditView.__init__(self, context, request)

    def changed(self):
        admincomment = self.request.form.get('field.admincomment')

        if admincomment:
            # No verification is needed since this page is protected by
            # lp.Admin
            owner = IPerson(self.request.principal, None)
            self.context.recipient = owner.id
            self.context.active = True
            # now redirect to view the SignedCoC
            self.request.response.redirect(self.request.URL[-1])

        # XXX: cprov 20050226
        # How to proceed with no admincomment ?

class SignedCodeOfConductDeactiveView(EditView):
    """Deactive a SignedCodeOfConduct Entry.
    When deactivating a signature:
     * Grant admincomment,
     * store recipient,
     * clear active.
    """

    __used_for__ = ISignedCodeOfConduct

    ow = CustomWidgetFactory(ObjectWidget, SignedCodeOfConduct)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw

    def __init__(self, context, request):
        self.context = context
        self.request = request
        EditView.__init__(self, context, request)

    def changed(self):
        admincomment = self.request.form.get('field.admincomment')

        if admincomment:
            # No verification is needed since this page is protected by
            # lp.Edit
            owner = IPerson(self.request.principal, None)
            self.context.recipient = owner.id
            self.context.active = False
            # now redirect to view the SignedCoC
            self.request.response.redirect(self.request.URL[-1])

            
        # XXX: cprov 20050226
        # How to proceed with no admincomment ?


class PersonSignedCodesOfConductView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.message = None
        self.user = getUtility(ILaunchBag).user

    def signatures(self):
        """ """
        # use utility to query on SignedCoCs
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        return sCoC_util.searchByUser(self.user.id)


    def performChanges(self):
        """  """
        sign_ids = self.request.form.get("DEACTIVE_SIGN")

        self.message = 'Deactivating: '

        if sign_ids is not None:
            sCoC_util = getUtility(ISignedCodeOfConductSet)

            # verify if we have multiple entries to deactive
            if not isinstance(sign_ids, list):
                sign_ids = [sign_ids]

            for sign_id in sign_ids:
                sign_id = int(sign_id)
                self.message += '%d,' % sign_id
                sCoC_util.deactivateSignature(sign_id)

            return True









