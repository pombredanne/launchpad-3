# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211, E0213

"""A collection of branches."""

__metaclass__ = type
__all__ = [
    'all_branches',
    'IBranchCollection',
    ]

from zope.component import getUtility
from zope.interface import Interface

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class IBranchCollection(Interface):
    """A collection of branches.

    An `IBranchCollection` is an immutable collection of branches. It has two
    kinds of methods: filter methods and query methods.

    Query methods get information about the contents of collection. See
    `IBranchCollection.count` and `IBranchCollection.getBranches`.

    Filter methods return new IBranchCollection instances that have some sort
    of restriction. Examples include `ownedBy`, `visibleByUser` and
    `inProduct`.
    """

    # Note to developers: This interface should be extended with more query
    # methods. It would be great to have methods like getRecentRevisions on
    # arbitrary branch collections. Other statistical methods would be good
    # too, e.g. number of different branch owners in this collection.

    # XXX JonathanLange 2009-02-17: At the moment, there is no direct Zope
    # security for IBranchCollection providers. That is, you can call any
    # method you want on such a provider. The IBranches they return are
    # security proxied though.

    def count():
        """The number of branches in this collection."""

    def getBranches():
        """Return a result set of all branches in this collection."""

    def inProduct(product):
        """Restrict the collection to branches in 'product'."""

    def inProject(project):
        """Restrict the collection to branches in 'project'."""

    def inSourcePackage(package):
        """Restrict the collection to branches in 'package'."""

    def ownedBy(person):
        """Restrict the collection to branches owned by 'person'."""

    def registeredBy(person):
        """Restrict the collection to branches registered by 'person'."""

    def relatedTo(person):
        """Restrict the collection to branches related to 'person'.

        That is, branches that 'person' owns, registered or is subscribed to.
        """

    def subscribedBy(person):
        """Restrict the collection to branches subscribed to by 'person'."""

    def visibleByUser(person):
        """Restrict the collection to branches that person is allowed to see.
        """

    def withLifecycleStatus(*statuses):
        """Restrict the collection to branches with the given statuses."""


def all_branches(store=None):
    """Return a collection that represents all branches in Launchpad."""
    if store is None:
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    return IBranchCollection(store)
