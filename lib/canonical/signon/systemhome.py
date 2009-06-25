# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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
