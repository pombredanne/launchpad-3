# Copyright 2008-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Interface for branch targets.

A branch target is the 'thing' that a branch is on. Branches in Launchpad are
owned by an IPerson and can be either junk branches, product branches or
package branches. A branch target is the product or package that a branch is
on. If the branch is a junk branch, then the target is the branch owner.
"""

__metaclass__ = type
__all__ = [
    'check_default_stacked_on',
    'IBranchTarget',
    'IHasBranchTarget',
    ]

from zope.interface import Attribute, Interface
from zope.security.interfaces import Unauthorized

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import IPrimaryContext
from lazr.restful.fields import Reference


def check_default_stacked_on(branch):
    """Return 'branch' if suitable to be a default stacked-on branch.

    Only certain branches are suitable to be default stacked-on branches.
    Branches that are *not* suitable include:
      - remote branches
      - branches the user cannot see
      - branches that have not yet been successfully processed by the puller.

    If the given branch is not suitable, return None. For convenience, also
    returns None if passed None. Otherwise, return the branch.
    """
    # Import here to avoid circular imports.
    from lp.code.interfaces.branch import BranchType
    if branch is None:
        return None
    try:
        branch_type = branch.branch_type
    except Unauthorized:
        return None
    if branch_type == BranchType.REMOTE:
        return None
    if branch.last_mirrored is None:
        return None
    return branch


class IHasBranchTarget(Interface):
    """A thing that has a branch target."""

    target = Attribute("The branch target, as an `IBranchTarget`.")


class IBranchTarget(IPrimaryContext):
    """A target of branches.

    A product contains branches, a source package on a distroseries contains
    branches, and a person contains 'junk' branches.
    """

    name = Attribute("The name of the target.")

    components = Attribute(
        "An iterable of the objects that make up this branch target, from "
        "most-general to most-specific. In a URL, these would normally "
        "appear from left to right.")

    displayname = Attribute("The display name of this branch target.")

    default_stacked_on_branch = Reference(
        # Should be an IBranch, but circular imports prevent it.
        schema=Interface,
        title=_("Default stacked-on branch"),
        required=True, readonly=True,
        description=_(
            'The branch that new branches will be stacked on by default.'))

    def __eq__(other):
        """Is this target the same as another target?

        Generally implemented in terms of `IPrimaryContext.context`.
        """

    def __ne__(other):
        """Is this target not the same as another target?

        Generally implemented in terms of `IPrimaryContext.context`.
        """

    def getNamespace(owner):
        """Return a `IBranchNamespace` for 'owner' and this target."""

    collection = Attribute("An IBranchCollection for this target.")

