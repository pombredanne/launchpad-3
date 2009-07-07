# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211, E0213

"""A collection of revisions.

See `IRevisionCollection` for more details.
"""

__metaclass__ = type
__all__ = [
    'IRevisionCache',
    'IRevisionCollection',
    ]

from zope.interface import Interface


class IRevisionCollection(Interface):
    """A collection of revisions.

    An `IRevisionCollection` is an immutable collection of revisions. It has
    two kinds of methods: filter methods and query methods.

    Query methods get information about the contents of collection. See
    `IRevisionCollection.getRevisions` and
    `IRevisionCollection.getRevisionAuthors`.

    Filter methods return new IRevisionCollection instances that have some sort
    of restriction. Examples include `inProduct`, and `arePublic`.

    Implementations of this interface are not 'content classes'. That is, they
    do not correspond to a particular row in the database.

    This interface is intended for use within Launchpad, not to be exported as
    a public API.
    """

    def count():
        """The number of revisions in this collection."""

    def getRevisions():
        """Return a result set of all distinct revisions in this collection.
        """

    def inProduct(product):
        """Restrict the collection to branches in 'product'."""

    def inProject(project):
        """Restrict the collection to branches in 'project'."""

    def inSourcePackage(package):
        """Restrict the collection to branches in 'package'.

        A source package is effectively a sourcepackagename in a distro
        series.
        """

    def inDistribution(distribution):
        """Restrict the collection to branches in 'distribution'."""

    def inDistroSeries(distro_series):
        """Restrict the collection to branches in 'distro_series'."""

    def inDistributionSourcePackage(distro_source_package):
        """Restrict to branches in a 'package' for a 'distribution'."""

    def authoredBy(person):
        """Restrict the collection to branches owned by 'person'."""


class IRevisionCache(IRevisionCollection):
    """An `IRevisionCollection` representing recent revisions in Launchpad.

    In order to have efficient queries, only revisions in the last 30 days are
    cached for fast counting and access.

    The revisions that are returned from the cache are used for counts on
    summary pages and to populate the feeds.
    """
