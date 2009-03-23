# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Utility for looking up branches by name."""

__metaclass__ = type
__all__ = [
    'IBranchLookup',
    ]

from zope.interface import Interface


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

    def getByUrl(url, default=None):
        """Find a branch by URL.

        Either from the external specified in Branch.url, from the URL on
        http://bazaar.launchpad.net/ or the lp: URL.

        Return the default value if no match was found.
        """

    def getByLPPath(path):
        """Find the branch associated with an lp: path.

        Recognized formats:
        "~owner/product/name" (same as unique name)
        "product/series" (branch associated with a product series)
        "product" (development focus of product)

        :return: a tuple of `IBranch`, extra_path, series.  Series is the
            series, if any, used to perform the lookup.
        :raises: `BranchNotFound`, `NoBranchForSeries`, and other subclasses
            of `LaunchpadFault`.
        """
