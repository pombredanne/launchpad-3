# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for linking BugTasks and Branches."""

__metaclass__ = type

__all__ = [
    "IBugBranch",
    "IBugBranchSet",
    ]

from lazr.restful.declarations import (
    export_as_webservice_entry,
    exported,
    )
from lazr.restful.fields import ReferenceChoice
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import Object

from lp import _
from lp.bugs.interfaces.hasbug import IHasBug
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.person import IPerson
from lp.services.fields import BugField


class IBugBranch(IHasBug):
    """A branch linked to a bug."""

    export_as_webservice_entry()

    bug = exported(
        BugField(
            title=_("Bug #"),
            required=True, readonly=True))
    branch = exported(
        ReferenceChoice(
            title=_("Branch"), schema=IBranch,
            vocabulary="Branch", required=True))

    datecreated = Attribute("The date on which I was created.")
    registrant = Object(
        schema=IPerson, readonly=True, required=True,
        title=_("The person who linked the bug to the branch"))


class IBugBranchSet(Interface):

    def getBranchesWithVisibleBugs(branches, user):
        """Find which of `branches` are for bugs that `user` can see.

        :param branches: A sequence of `Branch`es to limit the search
            to.
        :return: A result set of `Branch` ids: a subset of the ids
            found in `branches`, but limited to branches that are
            visible to `user`.
        """
