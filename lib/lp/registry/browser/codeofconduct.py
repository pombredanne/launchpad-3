# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes to handle signed Codes of Conduct."""

__metaclass__ = type

__all__ = [
    'SignedCodeOfConductSetNavigation',
    'CodeOfConductSetNavigation',
    'CodeOfConductOverviewMenu',
    'CodeOfConductSetOverviewMenu',
    'SignedCodeOfConductSetOverviewMenu',
    'SignedCodeOfConductOverviewMenu',
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

from canonical.launchpad.webapp import (
    ApplicationMenu, canonical_url, enabled_with_permission,
    GetitemNavigation, LaunchpadView, Link)
from canonical.launchpad.webapp.launchpadform import action, LaunchpadFormView
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.registry.interfaces.codeofconduct import (
    ICodeOfConduct, ICodeOfConductConf, ICodeOfConductSet,
    ISignedCodeOfConduct, ISignedCodeOfConductSet)
from lp.registry.interfaces.person import IPerson
class SignedCodeOfConductSetNavigation(GetitemNavigation):

    usedfor = ISignedCodeOfConductSet


class CodeOfConductSetNavigation(GetitemNavigation):

    usedfor = ICodeOfConductSet


class CodeOfConductOverviewMenu(ApplicationMenu):

    usedfor = ICodeOfConduct
    facet = 'overview'
    links = ['sign', 'download']

    def sign(self):
        text = 'Sign it'
        if (self.context.current and
            self.user and
            not self.user.is_ubuntu_coc_signer):
            # Then...
            enabled = True
        else:
            enabled = False
        return Link('+sign', text, enabled=enabled, icon='edit')

    def download(self):
        text = 'Download this version'
        is_current = self.context.current
        return Link('+download', text, enabled=is_current, icon='download')


class CodeOfConductSetOverviewMenu(ApplicationMenu):

    usedfor = ICodeOfConductSet
    facet = 'overview'
    links = ['admin']

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administration console'
        return Link('console', text, icon='edit')


class SignedCodeOfConductSetOverviewMenu(ApplicationMenu):

    usedfor = ISignedCodeOfConductSet
    facet = 'overview'
    links = ['register']

    def register(self):
        text = "Register Someone's Signature"
        return Link('+new', text, icon='add')


class SignedCodeOfConductOverviewMenu(ApplicationMenu):

    usedfor = ISignedCodeOfConduct
    facet = 'overview'
    links = ['activation', 'adminconsole']

    def activation(self):
        if self.context.active:
            text = 'deactivate'
            return Link('+deactivate', text, icon='edit')
        else:
            text = 'activate'
            return Link('+activate', text, icon='edit')

    def adminconsole(self):
        text = 'Administration console'
        return Link('../', text, icon='info')


class CodeOfConductView(LaunchpadView):
    """Simple view class for CoC page."""

    @property
    def page_title(self):
        """See `LaunchpadView`."""
        # This page has no breadcrumbs, nor should it.
        return self.context.title


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
        self.request.response.setHeader(
            'Content-Disposition', 'attachment; filename="%s"' % filename)
        return content


class CodeOfConductSetView(LaunchpadView):
    """Simple view class for CoCSet page."""


class SignedCodeOfConductAddView(LaunchpadFormView):
    """Add a new SignedCodeOfConduct Entry."""
    schema = ISignedCodeOfConduct
    field_names = ['signedcode']

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        signedcode = data["signedcode"]
        signedcocset = getUtility(ISignedCodeOfConductSet)
        error_message = signedcocset.verifyAndStore(self.user, signedcode)
        # It'd be nice to do this validation before, but the method which does
        # the validation is also the one that stores the signed CoC, so we
        # need to do everything here.
        if error_message:
            self.addError(error_message)
            return
        self.next_url = canonical_url(self.user) + '/+codesofconduct'

    @property
    def current(self):
        """Return the current release of the Code of Conduct."""
        coc_conf = getUtility(ICodeOfConductConf)
        coc_set = getUtility(ICodeOfConductSet)
        return coc_set[coc_conf.currentrelease]


class SignedCodeOfConductAckView(AddView):
    """Acknowledge a Paper Submitted CoC."""


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


# XXX: salgado, bug=414861, 2009-08-17: This view must be converted to a
# LaunchpadFormView and define a 'cancel_url' so that the form gets a cancel
# link.
class SignedCodeOfConductActiveView(EditView):
    """Active a SignedCodeOfConduct Entry.
    When activating a signature:
     * Grant a new admincomment,
     * store the recipient,
     * set active.
    """


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


# XXX: salgado, bug=414857, 2009-08-17: This view must be converted to a
# LaunchpadFormView and define a 'cancel_url' so that the form gets a cancel
# link.
class SignedCodeOfConductDeactiveView(EditView):
    """Deactive a SignedCodeOfConduct Entry.
    When deactivating a signature:
     * Grant admincomment,
     * store recipient,
     * clear active.
    """


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

