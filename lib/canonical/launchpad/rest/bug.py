# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad bugs."""

__metaclass__ = type
__all__ = [
    'BugCollection',
    'bugcomment_to_entry',
    ]

from zope.component import getUtility

from canonical.lazr.rest import Collection
from canonical.lazr.interfaces.rest import IEntry

from canonical.launchpad.interfaces import IBugSet


class BugCollection(Collection):
    """A collection of bugs, as exposed through the web service."""

    def find(self):
        """Return all the bugs on the site."""
        # Our context here is IMaloneApplication, that's why
        # we need getUtility.
        return getUtility(IBugSet).searchAsUser(None)


def bugcomment_to_entry(comment):
    """Will adapt to the bugcomment to the real IMessage.

    This is needed because navigation to comments doesn't return
    real IMessage instances but IBugComment.
    """
    return IEntry(comment.bugtask.bug.messages[comment.index])
