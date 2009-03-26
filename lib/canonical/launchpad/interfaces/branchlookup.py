# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Utility for looking up branches by name."""

__metaclass__ = type
__all__ = [
    'CannotHaveLinkedBranch',
    'IBranchLookup',
    'ICanHasLinkedBranch',
    'ILinkedBranchTraversable',
    'ILinkedBranchTraverser',
    'InvalidBranchIdentifier',
    'ISourcePackagePocket',
    'ISourcePackagePocketFactory',
    'NoLinkedBranch',
    ]

from zope.interface import Attribute, Interface
from zope.traversing.interfaces import ITraversable, ITraverser


class InvalidBranchIdentifier(Exception):
    """Raised when trying to resolve an invalid branch name."""

    def __init__(self, path):
        self.path = path
        Exception.__init__(self, "Invalid branch identifier: '%s'" % (path,))


class CannotHaveLinkedBranch(Exception):
    """Raised when we try to look up the linked branch for a thing that can't.
    """

    def __init__(self, component):
        self.component = component
        Exception.__init__(
            self, "%r cannot have linked branches." % (component,))


class NoLinkedBranch(Exception):
    """Raised when there's no linked branch for a thing."""

    def __init__(self, component):
        self.component = component
        Exception.__init__(self, "%r has no linked branch." % (component,))


class ICanHasLinkedBranch(Interface):
    """Something that has a linked branch."""

    branch = Attribute("The linked branch.")


class ILinkedBranchTraversable(ITraversable):
    """A thing that can be traversed to find a thing linked to a branch."""


class ILinkedBranchTraverser(ITraverser):
    """Utility for traversing to an object that can have a linked branch."""

    def traverse(path):
        """Traverse to the linked object referred to by 'path'.

        :raises NoSuchBranch: If we can't find a branch that matches the
            branch component of the path.
        :raises NoSuchPerson: If we can't find a person who matches the person
            component of the path.
        :raises NoSuchProduct: If we can't find a product that matches the
            product component of the path.
        :raises NoSuchProductSeries: If the series component doesn't match an
            existing series.
        :raises NoSuchSourcePackageName: If the source packagae referred to
            does not exist.

        :return: One of
            * `IProduct`
            * `IProductSeries`
            * (ISourcePackage, PackagePublishingPocket)
            * `IDistributionSourcePackage`
        """


class IBranchLookup(Interface):
    """Utility for looking up a branch by name."""

    def get(branch_id, default=None):
        """Return the branch with the given id.

        Return the default value if there is no such branch.
        """

    def getByUniqueName(unique_name):
        """Find a branch by its ~owner/product/name unique name.

        Return None if no match was found.
        """

    def uriToUniqueName(uri):
        """Return the unique name for the URI, if the URI is on codehosting.

        This does not ensure that the unique name is valid.  It recognizes the
        codehosting URIs of remote branches and mirrors, but not their
        remote URIs.

        :param uri: An instance of lazr.uri.URI
        :return: The unique name if possible, None if the URI is not a valid
            codehosting URI.
        """

    def getByUrl(url):
        """Find a branch by URL.

        Either from the external specified in Branch.url, from the URL on
        http://bazaar.launchpad.net/ or the lp: URL.

        Return None if no match was found.
        """

    def getByLPPath(path):
        """Find the branch associated with an lp: path.

        Recognized formats:
        "~owner/product/name" (same as unique name)
        "distro/series/sourcepackage" (official branch for release pocket of
            the version of a sourcepackage in a distro series)
        "product/series" (branch associated with a product series)
        "product" (development focus of product)

        :raises InvalidBranchIdentifier: If the given path could never
            possibly match a branch.
        :raises InvalidProductName: If the given product in a product
            or product series shortcut is an invalid name for a product.
        :raises NoBranchForSeries: If the product series referred to does not
            have an associated branch.
        :raises NoBranchForSourcePackage: If there is no official branch at
            the path described.
        :raises NoDefaultBranch: If there is no default branch possible for
            the given shortcut.
        :raises NoSuchBranch: If we can't find a branch that matches the
            branch component of the path.
        :raises NoSuchPerson: If we can't find a person who matches the person
            component of the path.
        :raises NoSuchProduct: If we can't find a product that matches the
            product component of the path.
        :raises NoSuchProductSeries: If the series component doesn't match an
            existing series.
        :raises NoSuchSourcePackageName: If the source packagae referred to
            does not exist.

        :return: a tuple of `IBranch`, extra_path. 'extra_path' is used to
            make things like 'bzr cat lp:~foo/bar/baz/README' work.
        """


class ISourcePackagePocketFactory(Interface):
    """Utility for constructing source package pocket wrappers."""

    def new(package, pocket):
        """Construct a new `ISourcePackagePocket`.

        :param package: An `ISourcePackagePocket`.
        :param pocket: A `DBItem` of `PackagePublishingPocket`.
        :return: `ISourcePackagePocket`.
        """


class ISourcePackagePocket(ICanHasLinkedBranch):
    """A wrapper around a source package and a pocket.

    Used to provide a single object that can be used in exceptions about a
    sourcepackage and a pocket not having an official linked branch.
    """

    displayname = Attribute("The display name")
    path = Attribute("The path of the source package pocket.")
    pocket = Attribute("The pocket.")
    sourcepackage = Attribute("The source package.")
    suite = Attribute(
        "The name of the suite. The distro series name and the pocket name.")

    def __eq__(other):
        """Is this source package pocket equal to another?

        True if and only if the package and pocket of the other are equal to
        our package and pocket.
        """

    def __ne__(other):
        """Is this source package pocket not equal to another?

        True if and only if self and other are not equal.
        """
