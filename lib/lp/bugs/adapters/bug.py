# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Resources having to do with Launchpad bugs."""

__metaclass__ = type
__all__ = [
    'bugcomment_to_entry',
    ]

from lazr.restful.interfaces import IEntry

def bugcomment_to_entry(comment):
    """Will adapt to the bugcomment to the real IMessage.

    This is needed because navigation to comments doesn't return
    real IMessage instances but IBugComment.
    """
    return IEntry(comment.bugtask.bug.messages[comment.index])
