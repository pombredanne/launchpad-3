# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = [
    "ISpecificationBranch",
    "ISpecificationBranchSet",
    ]

from zope.interface import Interface
from zope.schema import Choice, Int

from canonical.launchpad import _
from canonical.launchpad.fields import Summary
from canonical.launchpad.interfaces import IHasDateCreated


class ISpecificationBranch(IHasDateCreated):
    """A branch linked to a specification."""

    id = Int(title=_("Specification Branch #"))
    specification = Int(title=_("Specification"))
    branch = Choice(
        title=_("Branch"), vocabulary="Branch")
    summary = Summary(title=_("Summary"), required=False)

    def destroySelf():
        """Destroy this specification branch link"""


class ISpecificationBranchSet(Interface):

    def getSpecificationBranchesForBranches(branches, user):
        """Return a sequence of ISpecificationBranch instances associated with
        the given branches.

        Only return instances that are visible to the user.
        """
