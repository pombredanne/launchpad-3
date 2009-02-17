# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Interface for branch targets.

A branch target is the 'thing' that a branch is on. Branches in Launchpad are
owned by an IPerson and can be either junk branches, product branches or
package branches. A branch target is the product or package that a branch is
on. If the branch is a junk branch, then the target is the branch owner.
"""

__metaclass__ = type
__all__ = [
    'IBranchTarget',
    ]

from zope.interface import Interface, Attribute


class IBranchTarget(Interface):
    """A target of branches.

    A product contains branches, a source package on a distroseries contains
    branches, and a person contains 'junk' branches.
    """

    name = Attribute("The name of the target.")

    def getNamespace(owner):
        """Return a namespace for this target and the specified owner."""
