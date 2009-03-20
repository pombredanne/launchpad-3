# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Utility for looking up branches by name."""

__metaclass__ = type
__all__ = [
    'IBranchLookup',
    'InvalidBranchIdentifier',
    'NoBranchForSeries',
    'NoBranchForSourcePackage',
    'NoDefaultBranch',
    ]

from zope.interface import Interface


class InvalidBranchIdentifier(Exception):
    """Raised when trying to resolve an invalid branch name."""

    def __init__(self, path):
        self.path = path
        Exception.__init__(self, "Invalid branch identifier: '%s'" % (path,))


class NoBranchForSeries(Exception):
    """Raised when we wrongly assume a product series has a branch."""

    def __init__(self, product_series):
        self.series = product_series
        Exception.__init__(self, "%r has no branch" % (product_series,))


# XXX: Perhaps NoBranchForSeries and NoBranchForSourcePackage could share a
# base class?
class NoBranchForSourcePackage(Exception):
    """Raised when we wrongly assume a source package has a branch."""

    def __init__(self, sourcepackage, pocket):
        self.sourcepackage = sourcepackage
        self.pocket = pocket
        # XXX: Exception message doesn't include pocket -- is kind of crap.
        Exception.__init__(self, "%r has no branch" % (sourcepackage,))


class NoDefaultBranch(Exception):
    """Raised when asked to resolve a path that never has a default branch."""

    def __init__(self, component, component_type):
        self.component = component
        self.component_type = component_type
        Exception.__init__(self, "%r has no default branch." % (component,))


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

        :return: a tuple of `IBranch`, extra_path, series. 'series' is the
            series, if any, used to perform the lookup. It's returned so that
            we can raise informative errors when we match a private branch.
            'extra_path' is used to make things like 'bzr cat
            lp:~foo/bar/baz/README' work.
        """
