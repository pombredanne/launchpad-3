# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interface for the linker between Project and Bounty."""

__metaclass__ = type

__all__ = [
    'IProjectBounty',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int
from canonical.launchpad import _

class IProjectBounty(Interface):
    """The relationship between a project and a bounty."""

    id = Int(title=_('ID'), readonly=True, required=True)
    project = Choice(
        title=_('Project'), required=True, vocabulary='Project',
        readonly=True)
    bounty = Choice(title=_('Bounty'), required=True, readonly=True,
        vocabulary='Bounty', description=_("The existing Launchpad "
        "bounty, which you would like to show as being related to this "
        "project."))

