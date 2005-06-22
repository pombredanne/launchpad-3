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
from zope.exceptions import NotFoundError
import zope.security.interfaces

from canonical.database.constants import UTC_NOW

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
    
    def __init__(self, context, request):
        self.context = context
        self.request = request


class CodeOfConductDownloadView(object):
    """Download view class for CoC page.

    This view does not use a template, but uses a __call__ method
    that returns a file to the browser.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Set response headers to download an attachment, and return
        CoC file data.
        """
        # Use the context attribute 'content' as data to return.
        # Avoid open the CoC file again.
        content = self.context.content

        # Build a fancy filename:
        # - Use title with no spaces and append '.txt'
        filename = self.context.title.replace(' ', '') + '.txt'
        
        self.request.response.setHeader('Content-Type', 'application/text')
        self.request.response.setHeader('Content-Length', len(content))
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename="%s"' % filename)
        return content


class CodeOfConductSetView(object):
    """Simple view class for CoCSet page."""
    
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
        self.page_title = self.label
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
        kw['user'] = owner

        # use utility to store it in the database
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        info = sCoC_util.verifyAndStore(**kw)

        # xxx cprov 20050328
        # raising wrong exception 
        if info != None:
            raise NotFoundError(info)
        
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
        self.page_title = self.label
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        """Verify and Add the Acknowledge SignedCoC entry."""
        kw = {}
        
        for key, value in data.items():
            kw[str(key)] = value

        # XXX cprov 20050323
        # rename unused key:value
        kw['user'] = kw['owner']
        del kw['owner']

        recipient = IPerson(self.request.principal, None)
        kw['recipient'] = recipient
        
        # use utility to store it in the database
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        sCoC_util.acknowledgeSignature(**kw)

    def nextURL(self):
        return self._nextURL


class SignedCodeOfConductView(object):
    """Simple view class for SignedCoC page."""
    
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
        self.page_title = self.label
        EditView.__init__(self, context, request)

    def changed(self):
        self.context.datecreated = UTC_NOW
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
        self.page_title = self.label
        EditView.__init__(self, context, request)

    def changed(self):
        admincomment = self.request.form.get('field.admincomment')

        if admincomment:
            # No verification is needed since this page is protected by
            # lp.Admin
            recipient = IPerson(self.request.principal, None)
            kw = {}
            kw['recipient'] = recipient
            kw['admincomment'] = admincomment
            kw['sign_id'] = self.context.id
            kw['state'] = True
            
            # use utility to active it in the database
            sCoC_util = getUtility(ISignedCodeOfConductSet)
            sCoC_util.modifySignature(**kw)

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
        self.page_title = self.label
        EditView.__init__(self, context, request)

    def changed(self):
        admincomment = self.request.form.get('field.admincomment')

        if admincomment:
            # No verification is needed since this page is protected by
            # lp.Edit
            recipient = IPerson(self.request.principal, None)

            kw = {}
            kw['recipient'] = recipient
            kw['admincomment'] = admincomment
            kw['sign_id'] = self.context.id
            kw['state'] = False

            # use utility to active it in the database
            sCoC_util = getUtility(ISignedCodeOfConductSet)
            sCoC_util.modifySignature(**kw)

            # now redirect to view the SignedCoC
            self.request.response.redirect(self.request.URL[-1])

            
        # XXX: cprov 20050226
        # How to proceed with no admincomment ?








