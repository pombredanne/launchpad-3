# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Classes related to OpenID discovery."""

__metaclass__ = type
__all__ = []

from zope.component import getUtility
from zope.interface import implements

from z3c.ptcompat import ViewPageTemplateFile

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces.account import AccountStatus, IAccountSet
from canonical.launchpad.interfaces.authtoken import IAuthTokenSet
from canonical.signon.interfaces.openidserver import IOpenIDApplication
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.publisher import (
    Navigation, stepthrough, stepto)
from lp.services.openid.interfaces.openid import IOpenIDPersistentIdentity
from lp.services.openid.browser.openiddiscovery import (
    XRDSContentNegotiationMixin)
from canonical.signon.interfaces.ssoaccount import ISSOAccount


class OpenIDApplicationURL:
    """Canonical URL data for `IOpenIDApplication`"""
    implements(ICanonicalUrlData)

    path = ''
    inside = None
    rootsite = 'openid'

    def __init__(self, context):
        self.context = context


class OpenIDApplicationNavigation(Navigation):
    """Navigation for `IOpenIDApplication`"""
    usedfor = IOpenIDApplication

    @stepthrough('+id')
    def traverse_id(self, name):
        """Traverse to persistent OpenID identity URLs."""
        try:
            account = getUtility(IAccountSet).getByOpenIDIdentifier(name)
        except LookupError:
            account = None
        if account is None or account.status != AccountStatus.ACTIVE:
            return None
        return IOpenIDPersistentIdentity(account)

    @stepto('token')
    def token(self):
        """Traverse to auth tokens."""
        # We need to traverse the 'token' namespace in order to allow people
        # to create new accounts and reset their passwords. This can't clash
        # with a person's name because it's a blacklisted name.
        return getUtility(IAuthTokenSet)


class PersistentIdentityView(XRDSContentNegotiationMixin, LaunchpadView):
    """Render the OpenID identity page."""

    xrds_template = ViewPageTemplateFile("../templates/person-xrds.pt")

    @cachedproperty
    def openid_identity_url(self):
        """The person's persistent OpenID identity URL."""
        return self.context.openid_identity_url


class OpenIDApplicationIndexView(XRDSContentNegotiationMixin, LaunchpadView):
    """Render the OpenID index page."""

    template = ViewPageTemplateFile(
        "../templates/openid-index.pt")
    xrds_template = ViewPageTemplateFile(
        "../templates/openidapplication-xrds.pt")

    @property
    def sso_account(self):
        return ISSOAccount(self.account)
