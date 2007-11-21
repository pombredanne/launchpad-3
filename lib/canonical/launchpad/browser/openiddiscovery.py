# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Classes related to OpenID discovery."""

__metaclass__ = type
__all__ = []

from openid.yadis.accept import getAcceptable
from openid.yadis.constants import YADIS_CONTENT_TYPE, YADIS_HEADER_NAME

from zope.component import getUtility
from zope.interface import implements
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.launchpad.interfaces import (
    ILoginTokenSet, IOpenIdApplication, IOpenIDPersistentIdentity,
    IPersonSet, NotFoundError)
from canonical.launchpad.webapp import canonical_url, LaunchpadView
from canonical.launchpad.webapp.publisher import (
    Navigation, RedirectionView, stepthrough, stepto)
from canonical.launchpad.webapp.vhosts import allvhosts


class OpenIdApplicationNavigation(Navigation):
    usedfor = IOpenIdApplication

    @stepthrough('+id')
    def traverse_id(self, name):
        person = getUtility(IPersonSet).getByOpenIdIdentifier(name)
        if person is not None and person.is_openid_enabled:
            return OpenIDPersistentIdentity(person)
        else:
            return None

    @stepto('token')
    def token(self):
        # We need to traverse the 'token' namespace in order to allow people
        # to create new accounts and reset their passwords. This can't clash
        # with a person's name because it's a blacklisted name.
        return getUtility(ILoginTokenSet)

    def traverse(self, name):
        # Provide a permanent OpenID identity for use by the Ubuntu shop
        # or other services that cannot cope with name changes.
        person = getUtility(IPersonSet).getByName(name)
        if person is not None and person.is_openid_enabled:
            target = '%s+id/%s' % (
                    allvhosts.configs['openid'].rooturl,
                    person.openid_identifier)
            return RedirectionView(target, self.request, 303)
        else:
            raise NotFoundError(name)


class OpenIDPersistentIdentity:

    implements(IOpenIDPersistentIdentity)

    def __init__(self, person):
        self.person = person


class XRDSContentNegotiationMixin:
    """A mixin that does content negotiation to support XRDS discovery."""

    def xrds(self):
        self.request.response.setHeader('Content-Type', YADIS_CONTENT_TYPE)
        data = self.xrds_template()
        return data.encode('utf-8')

    def render(self):
        # Tell the user agent that we do different things depending on
        # the value of the "Accept" header.
        self.request.response.setHeader('Vary', 'Accept')

        accept_content = self.request.get('HTTP_ACCEPT', '')
        acceptable = getAcceptable(accept_content,
                                   ['text/html', YADIS_CONTENT_TYPE])
        # Show the XRDS if it is preferred to text/html
        for mtype in acceptable:
            if mtype == 'text/html':
                break
            elif mtype == YADIS_CONTENT_TYPE:
                return self.xrds()
            else:
                raise AssertionError(
                    'Unexpected acceptable content type: %s' % mtype)

        # Add a header pointing to the location of the XRDS document
        # and chain to the default render() method.
        self.request.response.setHeader(
            YADIS_HEADER_NAME, '%s/+xrds' % canonical_url(self.context))
        return super(XRDSContentNegotiationMixin, self).render()

    @property
    def openid_server_url(self):
        """The OpenID Server endpoint URL for Launchpad."""
        return allvhosts.configs['openid'].rooturl + '+openid'


class PersistentIdentityView(LaunchpadView):
    """Render the OpenID identity page."""

    identity_template = ViewPageTemplateFile(
        "../templates/openid-identity.pt")

    def render(self):
        # Setup variables to pass to the template
        self.server_url = allvhosts.configs['openid'].rooturl + '+openid'
        self.person = self.context.person
        self.identity_url = '%s+id/%s' % (
                self.server_url, self.person.openid_identifier)
        self.person_url = canonical_url(self.person, rootsite='mainsite')
        self.meta_refresh_content = "1; URL=%s" % self.person_url

        return self.identity_template()
