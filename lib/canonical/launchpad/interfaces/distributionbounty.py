# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# pylint: disable-msg=E0211,E0213
"""Interface for the linker between Distribution and Bounty."""

__metaclass__ = type

__all__ = [
    'IDistributionBounty',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int
from canonical.launchpad import _

class IDistributionBounty(Interface):
    """The relationship between a distribution and a bounty."""

    id = Int(title=_('ID'), readonly=True, required=True)
    distribution = Choice(
        title=_('Distribution'), required=True, vocabulary='Distribution',
        readonly=True)
    bounty = Choice(title=_('Bounty'), required=True, readonly=True,
        vocabulary='Bounty', description=_("The existing Launchpad "
        "bounty, which you would like to show as being related to this "
        "distribution."))

