# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interface for the linker between Product and Bounty."""

__metaclass__ = type

__all__ = [
    'IProductBounty',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int
from canonical.launchpad import _

class IProductBounty(Interface):
    """The relationship between a product and a bounty."""

    id = Int(title=_('ID'), readonly=True, required=True)
    product = Choice(
        title=_('Project'), required=True, vocabulary='Product',
        readonly=True)
    bounty = Choice(title=_('Bounty'), required=True, readonly=True,
        vocabulary='Bounty', description=_("The existing Launchpad "
        "bounty, which you would like to show as being related to "
        "this project."))

