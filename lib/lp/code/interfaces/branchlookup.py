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
    'NoLinkedBranch',
    ]

from zope.interface import Attribute, Interface


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


class ILinkedBranchTraversable(Interface):
    """A thing that can be traversed to find a thing linked to a branch."""

    def traverse(self, name):
        """Return the object beneath this one that matches 'name'."""


class ILinkedBranchTraverser(Interface):
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
        "distro/series-pocket/sourcepackage" (official branch for the given
            pocket of the version of a sourcepackage in a distro series)
        "product/series" (branch associated with a product series)
        "product" (development focus of product)

        :raises InvalidNamespace: If the path looks like a unique branch name
            but doesn't have enough segments to be a unique name.
        :raises InvalidProductName: If the given product in a product
            or product series shortcut is an invalid name for a product.

        :raises NoSuchBranch: If we can't find a branch that matches the
            branch component of the path.
        :raises NoSuchPerson: If we can't find a person who matches the person
            component of the path.
        :raises NoSuchProduct: If we can't find a product that matches the
            product component of the path.
        :raises NoSuchProductSeries: If the product series component doesn't
            match an existing series.
        :raises NoSuchDistroSeries: If the distro series component doesn't
            match an existing series.
        :raises NoSuchSourcePackageName: If the source packagae referred to
            does not exist.

        :raises NoLinkedBranch: If the path refers to an existing thing that's
            not a branch and has no default branch associated with it. For
            example, a product without a development focus branch.
        :raises CannotHaveLinkedBranch: If the path refers to an existing
            thing that cannot have a linked branch associated with it. For
            example, a distribution.

        :return: a tuple of (`IBranch`, extra_path). 'extra_path' is used to
            make things like 'bzr cat lp:~foo/bar/baz/README' work. Trailing
            paths are not handled for shortcut paths.
        """
