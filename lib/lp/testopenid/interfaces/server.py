# Copyright 2010 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'ITestOpenIDLoginForm',
    'ITestOpenIDApplication',
    ]

from zope.interface import Interface
from zope.schema import TextLine

from canonical.launchpad.fields import PasswordField
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication


class ITestOpenIDApplication(ILaunchpadApplication):
    """Launchpad's testing OpenID application root."""


class ITestOpenIDLoginForm(Interface):
    email = TextLine(title=u'What is your e-mail address?', required=True)
    password = PasswordField(title=u'Password', required=False)
    nonce = TextLine(
        title=u'Nonce', required=False, description=u'Unique value')
