# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad bugs."""

__metaclass__ = type
__all__ = [
    'bugcomment_to_entry',
    ]

from canonical.lazr.interfaces.rest import IEntry

def bugcomment_to_entry(comment):
    """Will adapt to the bugcomment to the real IMessage.

    This is needed because navigation to comments doesn't return
    real IMessage instances but IBugComment.
    """
    return IEntry(comment.bugtask.bug.messages[comment.index])
