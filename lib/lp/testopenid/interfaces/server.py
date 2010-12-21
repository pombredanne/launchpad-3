# Copyright 2010 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'get_server_url',
    'ITestOpenIDApplication',
    'ITestOpenIDLoginForm',
    'ITestOpenIDPersistentIdentity',
    ]

from zope.interface import Interface
from zope.schema import TextLine

from canonical.launchpad.webapp.interfaces import ILaunchpadApplication
from canonical.launchpad.webapp.url import urlappend
from canonical.launchpad.webapp.vhosts import allvhosts
from lp.services.fields import PasswordField
from lp.services.openid.interfaces.openid import IOpenIDPersistentIdentity


class ITestOpenIDApplication(ILaunchpadApplication):
    """Launchpad's testing OpenID application root."""


class ITestOpenIDLoginForm(Interface):
    email = TextLine(title=u'What is your e-mail address?', required=True)
    password = PasswordField(title=u'Password', required=True)


class ITestOpenIDPersistentIdentity(IOpenIDPersistentIdentity):
    """Marker interface for IOpenIDPersistentIdentity on testopenid."""


def get_server_url():
    """Return the URL for this server's OpenID endpoint.

    This is wrapped in a function (instead of a constant) to make sure the
    vhost.testopenid section is not required in production configs.
    """
    return urlappend(allvhosts.configs['testopenid'].rooturl, '+openid')
