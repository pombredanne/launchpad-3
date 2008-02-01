# Copyright 2008 Canonical Ltd.  All rights reserved.

"""CodeReviewMessage interfaces."""

__metaclass__ = type
__all__ = [
    'ICodeReviewMessage',
    ]

from zope.interface import Interface
from zope.schema import Object, Int

from canonical.launchpad import _
from canonical.launchpad.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from canonical.launchpad.interfaces.message import IMessage


class ICodeReviewMessage(Interface):
    """A link between a merge proposal and a message."""

    branch_merge_proposal = Object(schema=IBranchMergeProposal,
                                   title=_(u'The branch merge proposal'))
    message = Object(schema=IMessage, title=_(u'The message.'))
    vote = Int(title=_('vote'),
               description=_('The vote associated with this review message'))
