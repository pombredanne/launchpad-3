# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = ["ISpecificationBranch"]

from zope.interface import Interface
from zope.schema import Choice, Int, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import Summary
from canonical.launchpad.interfaces import (
    IHasDateCreated, non_duplicate_branch)


class ISpecificationBranch(IHasDateCreated):
    """A branch linked to a specification."""

    id = Int(title=_("Specification Branch #"))
    specification = Int(title=_("Specification"))
    branch = Choice(
        title=_("Branch"), vocabulary="Branch")
    summary = Summary(title=_("Summary"), required=False)

    def destroySelf():
        """Destroy this specification branch link"""
