# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = [
    "ISpecificationBranch",
    "ISpecificationBranchSet",
    ]

from zope.interface import Interface
from zope.schema import Int

from lazr.restful.fields import Reference, ReferenceChoice
from lazr.restful.declarations import (export_as_webservice_entry, exported,
    export_operation_as, export_write_operation)

from canonical.launchpad import _
from canonical.launchpad.fields import Summary
from canonical.launchpad.interfaces.launchpad import IHasDateCreated
from canonical.launchpad.interfaces.specification import ISpecification
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.person import IPerson


class ISpecificationBranch(IHasDateCreated):
    """A branch linked to a specification."""

    export_as_webservice_entry()

    id = Int(title=_("Specification Branch #"))

    specification = exported(
        ReferenceChoice(
            title=_("Blueprint"), vocabulary="Specification",
            readonly=True, schema=ISpecification))
    branch = exported(
        Reference(
            title=_("Branch"),
            readonly=True,
            schema=IBranch))
    summary = Summary(title=_("Summary"), required=False)

    registrant = exported(
        Reference(
            schema=IPerson, readonly=True, required=True,
            title=_("The person who linked the bug to the branch")))

    @export_operation_as('delete')
    @export_write_operation()
    def destroySelf():
        """Destroy this specification branch link"""


class ISpecificationBranchSet(Interface):
    """Methods that work on the set of all specification branch links."""

    def getSpecificationBranchesForBranches(branches, user):
        """Return a sequence of ISpecificationBranch instances associated with
        the given branches.

        Only return instances that are visible to the user.
        """
