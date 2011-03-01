# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = [
    "ISpecificationBranch",
    "ISpecificationBranchSet",
    ]

from lazr.restful.declarations import (
    export_as_webservice_entry,
    export_operation_as,
    export_write_operation,
    exported,
    )
from lazr.restful.fields import (
    Reference,
    ReferenceChoice,
    )
from zope.interface import Interface
from zope.schema import Int

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import IHasDateCreated
from lp.blueprints.interfaces.specification import ISpecification
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.person import IPerson


class ISpecificationBranch(IHasDateCreated):
    """A branch linked to a specification."""

    export_as_webservice_entry()

    id = Int(title=_("Specification Branch #"))
    specification = exported(
        ReferenceChoice(
            title=_("Blueprint"), vocabulary="Specification",
            required=True,
            readonly=True, schema=ISpecification))
    branch = exported(
        ReferenceChoice(
            title=_("Branch"),
            vocabulary="Branch",
            required=True,
            schema=IBranch))

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
