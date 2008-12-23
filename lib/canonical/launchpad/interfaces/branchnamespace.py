# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interface for a branch namespace."""

__metaclass__ = type
__all__ = [
    'get_branch_namespace',
    'IBranchNamespace',
    'IBranchNamespaceSet',
    'InvalidNamespace',
    'lookup_branch_namespace',
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute

from canonical.launchpad.interfaces.branch import BranchLifecycleStatus


class IBranchNamespace(Interface):
    """A namespace that a branch lives in."""

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

    def lookup(namespace_name):
        """Return the `IBranchNamespace` for 'namespace_name'.

        :raise InvalidNamespace: if namespace_name cannot be parsed.
        :raise NoSuchPerson: if the person referred to cannot be found.
        :raise NoSuchProduct: if the product referred to cannot be found.
        :raise NoSuchDistribution: if the distribution referred to cannot be
            found.
        :raise NoSuchDistroSeries: if the distroseries referred to cannot be-
            found.
        :raise NoSuchSourcePackageName: if the sourcepackagename referred to
            cannot be found.
        :return: An `IBranchNamespace`.
        """

    def parse(namespace_name):
        """Parse 'namespace_name' into its components.

        The name of a namespace is actually a path containing many elements,
        each of which maps to a particular kind of object in Launchpad.
        Elements that can appear in a namespace name are: 'person', 'product',
        'distribution', 'distroseries' and 'sourcepackagename'.

        'parse' returns a dict which maps the names of these elements (e.g.
        'person', 'product') to the values of these elements (e.g. 'sabdfl',
        'firefox'). If the given path doesn't include a particular kind of
        element, the dict maps that element name to None.

        For example::
            parse('~foo/bar') => {
                'person': 'foo', 'product': 'bar', 'distribution': None,
                'distroseries': None, 'sourcepackagename': None}

        If the given 'namespace_name' cannot be parsed, then we raise an
        `InvalidNamespace` error.

        :raise InvalidNamespace: if the name is too long, too short or is
            malformed.
        :return: A dict with keys matching each component in 'namespace_name'.
        """


class InvalidNamespace(Exception):
    """Raised when someone tries to lookup a namespace with a bad name.

    By 'bad', we mean that the name is unparseable. It might be too short, too
    long or malformed in some other way.
    """

    def __init__(self, name):
        self.name = name
        Exception.__init__(
            self, "Cannot understand namespace name: '%s'" % (name,))


def get_branch_namespace(person, product=None, distroseries=None,
                         sourcepackagename=None):
    return getUtility(IBranchNamespaceSet).get(
        person, product, distroseries, sourcepackagename)


def lookup_branch_namespace(namespace_name):
    return getUtility(IBranchNamespaceSet).lookup(namespace_name)
