# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = ["ISpecificationBranch"]

from zope.interface import Interface
from zope.schema import Choice, Int, Text

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IHasDateCreated, non_duplicate_branch)


class ISpecificationBranch(IHasDateCreated):
    """A branch linked to a specification."""

    id = Int(title=_("Specification Branch #"))
    specification = Int(title=_("Specification"))
    branch = Choice(
        title=_("Branch"), vocabulary="Branch")
    summary = Text(title=_("Summary"), required=False)
