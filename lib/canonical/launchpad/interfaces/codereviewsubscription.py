# Copyright 2008 Canonical Ltd.  All rights reserved.

"""CodeReviewSubscription interfaces."""

__metaclass__ = type
__all__ = [
    'ICodeReviewSubscription',
    ]

from zope.interface import Interface
from zope.schema import Object, Datetime

from canonical.launchpad import _
from canonical.launchpad.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from canonical.launchpad.interfaces.person import (
    IPerson)

class ICodeReviewSubscription(Interface):
    """A link between a merge proposal and an interested person."""

    branch_merge_proposal = Object(schema=IBranchMergeProposal,
                                   title=_(u'Branch merge proposal'))
    person = Object(schema=IPerson, title=_(u'Person subscribed.'))
    date_created = Datetime(title=_(u'Date created'))
    registrant = Object(
        schema=IPerson, title=_(u'Person who created the subscription.'))
