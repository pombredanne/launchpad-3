# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interface for a branch namespace."""

__metaclass__ = type
__all__ = [
    'get_branch_namespace',
    'IBranchNamespace',
    'IBranchNamespaceSet',
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute

from canonical.launchpad.interfaces.branch import BranchLifecycleStatus


class IBranchNamespace(Interface):
    """A namespace that a branch lives in."""

    owner = Attribute(
        "The `IPerson` who owns this namespace. Their name normally appears "
        "in the namespace's name.")
    name = Attribute(
        "The name of the namespace. This is prepended to the branch name.")

    def createBranch(branch_type, name, registrant, url=None, title=None,
                     lifecycle_status=BranchLifecycleStatus.NEW, summary=None,
                     whiteboard=None):
        """Create and return an `IBranch` in this namespace."""

    def createBranchWithPrefix(branch_type, prefix, registrant, url=None):
        """Create and return an `IBranch` with a name starting with 'prefix'.

        Use this method to automatically create a branch with an inferred
        name.
        """

    def findUnusedName(prefix):
        """Find an unused branch name starting with 'prefix'.

        Note that there is no guarantee that the name returned by this method
        will remain unused for very long. If you wish to create a branch with
        a given prefix, use createBranchWithPrefix.
        """

    def getBranches():
        """Return the branches in this namespace."""

    def getBranchName(name):
        """Get the potential unique name for a branch called 'name'."""

    def getByName(name, default=None):
        """Find the branch in this namespace called 'name'.

        :return: `IBranch` if found, 'default' if not.
        """

    def isNameUsed(name):
        """Is 'name' already used in this namespace?"""


class IBranchNamespaceSet(Interface):
    """Interface for getting branch namespaces.

    This interface exists *solely* to avoid importing things from the
    'database' package. Use `get_branch_namespace` to get branch namespaces
    instead.
    """

    def get(person, product, distroseries, sourcepackagename):
        """Return the appropriate `IBranchNamespace` for the given objects."""


def get_branch_namespace(person, product=None, distroseries=None,
                         sourcepackagename=None):
    return getUtility(IBranchNamespaceSet).get(
        person, product, distroseries, sourcepackagename)
