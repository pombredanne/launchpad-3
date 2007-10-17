# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View classes to handle signed Codes of Conduct."""

__metaclass__ = type

__all__ = [
    'SignedCodeOfConductSetNavigation',
    'CodeOfConductSetNavigation',
    'CodeOfConductContextMenu',
    'CodeOfConductSetContextMenu',
    'SignedCodeOfConductSetContextMenu',
    'SignedCodeOfConductContextMenu',
    'CodeOfConductView',
    'CodeOfConductDownloadView',
    'CodeOfConductSetView',
    'SignedCodeOfConductAddView',
    'SignedCodeOfConductAckView',
    'SignedCodeOfConductView',
    'SignedCodeOfConductAdminView',
    'SignedCodeOfConductActiveView',
    'SignedCodeOfConductDeactiveView',
    ]

from zope.app.form.browser.add import AddView, EditView
from zope.component import getUtility
from zope.app.form.interfaces import WidgetsError

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    GetitemNavigation, GeneralFormView)
from canonical.launchpad.interfaces import (
    IPerson, ILaunchBag, ICodeOfConduct, ISignedCodeOfConduct,
    ISignedCodeOfConductSet, ICodeOfConductSet, ICodeOfConductConf)


class SignedCodeOfConductSetNavigation(GetitemNavigation):

    usedfor = ISignedCodeOfConductSet


class CodeOfConductSetNavigation(GetitemNavigation):

    usedfor = ICodeOfConductSet


class CodeOfConductContextMenu(ContextMenu):

    usedfor = ICodeOfConduct
    links = ['sign', 'download']

    def sign(self):
        text = 'Sign this version'
        if self.context.current and self.user and not self.user.is_ubuntero:
            enabled = True
        else:
            enabled = False
        return Link('+sign', text, enabled=enabled, icon='edit')

    def download(self):
        text = 'Download this version'
        is_current=self.context.current
        return Link('+download', text, enabled=is_current, icon='download')


class CodeOfConductSetContextMenu(ContextMenu):

    usedfor = ICodeOfConductSet
    links = ['admin']

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administration console'
        return Link('console', text, icon='edit')


class SignedCodeOfConductSetContextMenu(ContextMenu):

    usedfor = ISignedCodeOfConductSet
    links = ['register']

    def register(self):
        text = "Register Someone's Signature"
        return Link('+new', text, icon='add')


class SignedCodeOfConductContextMenu(ContextMenu):

    usedfor = ISignedCodeOfConduct
    links = ['activation', 'adminconsole']

    def activation(self):
        if self.context.active:
            text = 'Deactivate Signature'
            return Link('+deactivate', text, icon='edit')
        else:
            text = 'Activate Signature'
            return Link('+activate', text, icon='edit')

    def adminconsole(self):
        text = 'Administration console'
        return Link('../', text, icon='info')


class CodeOfConductView:
    """Simple view class for CoC page."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)

class CodeOfConductDownloadView:
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


class CodeOfConductSetView:
    """Simple view class for CoCSet page."""

    def __init__(self, context, request):
        self.context = context
        self.request = request


class SignedCodeOfConductAddView(GeneralFormView):
    """Add a new SignedCodeOfConduct Entry."""

    def initialize(self):
        self.top_of_page_errors = []

    def validate(self, form_values):
        """Verify and Add SignedCoC entry"""
        signedcode = form_values["signedcode"]
        signedcocset = getUtility(ISignedCodeOfConductSet)
        error_message = signedcocset.verifyAndStore(self.user, signedcode)
        if error_message:
            self.top_of_page_errors.append(error_message)
            raise WidgetsError(self.top_of_page_errors)

    def nextURL(self):
        return canonical_url(self.user) + '/+codesofconduct'

    @property
    def getCurrent(self):
        """Return the current release of the Code of Conduct."""
        coc_conf = getUtility(ICodeOfConductConf)
        coc_set = getUtility(ICodeOfConductSet)
        return coc_set[coc_conf.currentrelease]


class SignedCodeOfConductAckView(AddView):
    """Acknowledge a Paper Submitted CoC."""

    __used_for__ = ICodeOfConduct

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

        # XXX cprov 2005-03-23:
        # rename unused key:value
        kw['user'] = kw['owner']
        del kw['owner']

        recipient = getUtility(ILaunchBag).user
        kw['recipient'] = recipient

        # use utility to store it in the database
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        sCoC_util.acknowledgeSignature(**kw)

    def nextURL(self):
        return self._nextURL


class SignedCodeOfConductView:
    """Simple view class for SignedCoC page."""

    def __init__(self, context, request):
        self.context = context
        self.request = request


class SignedCodeOfConductAdminView:
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

        if (self.request.method != "POST" or
            self.request.form.get("search") != "Search"):
            return

        # use utility to query on SignedCoCs
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        self.results = sCoC_util.searchByDisplayname(name,
                                                     searchfor=searchfor)

        return True


class SignedCodeOfConductActiveView(EditView):
    """Active a SignedCodeOfConduct Entry.
    When activating a signature:
     * Grant a new admincomment,
     * store the recipient,
     * set active.
    """

    __used_for__ = ISignedCodeOfConduct

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

        # XXX: cprov 2005-02-26:
        # How to proceed with no admincomment ?

class SignedCodeOfConductDeactiveView(EditView):
    """Deactive a SignedCodeOfConduct Entry.
    When deactivating a signature:
     * Grant admincomment,
     * store recipient,
     * clear active.
    """

    __used_for__ = ISignedCodeOfConduct

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


        # XXX: cprov 2005-02-26:
        # How to proceed with no admincomment ?

