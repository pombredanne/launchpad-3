# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Content classes for the 'home page' of SSO server."""

__all__ = [
    'OpenIDApplication',
    ]

__metaclass__ = type

from zope.interface import implements

from canonical.signon.interfaces.openidserver import IOpenIDApplication


class OpenIDApplication:
    implements(IOpenIDApplication)

    title = 'Launchpad Login Service'
