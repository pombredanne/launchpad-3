# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Link checker interfaces."""

__metaclass__ = type

__all__ = [
    'LinkCheckerAPI',
    'LinkCheckerURL',
    ]

from zope.interface import (
    implements,
    )

from canonical.launchpad.interfaces.linkchecker import ILinkCheckerAPI
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

class LinkCheckerAPI:
    """See `ILinkCheckerAPI`."""

    implements(ILinkCheckerAPI)

    def check_links(self, links):
        if links is None:
            links = ['a', 'b', 'c']
        return ','.join(links)


class LinkCheckerURL:
    """URL creation rules."""
    implements(ICanonicalUrlData)

    inside = None
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        """Return the path component of the URL."""
        return u'check_links'
