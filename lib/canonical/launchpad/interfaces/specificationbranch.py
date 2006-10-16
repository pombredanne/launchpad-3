# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = ["ISpecificationBranch"]

from zope.interface import Interface
from zope.schema import Int, Choice

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IHasDateCreated, non_duplicate_branch)
from canonical.lp.dbschema import SpecificationBranchStatus


class ISpecificationBranch(IHasDateCreated):
    """A branch linked to a specification."""

    id = Int(title=_("Specification Branch #"))
    specification = Int(title=_("Specification"))
    branch = Choice(
        title=_("Branch"), vocabulary="Branch")
