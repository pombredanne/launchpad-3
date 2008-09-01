# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A class for the top-level link to the authenticated user's account."""

__metaclass__ = type
__all__ = [
    'MeLink',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.interfaces import IPerson, IPersonSet

from canonical.lazr.interfaces.rest import ITopLevelEntryLink


class MeLink:
    """The top-level link to the authenticated user's account."""
    implements(ITopLevelEntryLink, ICanonicalUrlData)

    link_name = 'me'
    entry_type = IPerson

    @property
    def inside(self):
        """The +me link is beneath /people/."""
        return getUtility(IPersonSet)
    path = '+me'
    rootsite = 'api'

