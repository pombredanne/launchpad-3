# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Resources having to do with Launchpad bugs."""

__metaclass__ = type
__all__ = [
    'bugcomment_to_entry',
    'bugtask_to_privacy',
    ]

from lazr.restful.interfaces import IEntry
from zope.component import getMultiAdapter


def bugcomment_to_entry(comment, version):
    """Will adapt to the bugcomment to the real IMessage.

    This is needed because navigation to comments doesn't return
    real IMessage instances but IBugComment.
    """
    return getMultiAdapter(
        (comment.bugtask.bug.messages[comment.index], version), IEntry)

def bugtask_to_privacy(bugtask):
    """Adapt the bugtask to the underlying bug (which implements IPrivacy).

    Needed because IBugTask does not implement IPrivacy.
    """
    return bugtask.bug
