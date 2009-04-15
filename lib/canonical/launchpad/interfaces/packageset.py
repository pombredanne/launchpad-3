# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Packageset interfaces.

From http://en.wikipedia.org/wiki/Glossary_of_graph_theory:

If v is reachable from u, then u is a predecessor of v and v is a successor
of u. If there is an arc/edge from u to v, then u is a direct predecessor of
v, and v is a direct successor of u.
"""

__metaclass__ = type

__all__ = [
    'IPackageset',
    'IPackagesetSet',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, TextLine

from canonical.launchpad import _
from lp.registry.interfaces.person import IPerson
from canonical.launchpad.validators.name import name_validator
from canonical.lazr.fields import Reference


class IPackageset(Interface):
    """An interface for package sets."""

    id = Int(title=_('ID'), required=True, readonly=True)

    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True,
        description=_("The creation date/time for the package set at hand."))

    owner = Reference(
        IPerson, title=_("Person"), required=True, readonly=True,
        description=_("The person who owns the package set at hand."))

    name = TextLine(
        title=_('Valid package set name'),
        required=True, constraint=name_validator)

    description = TextLine(
        title=_("Description"), required=True, readonly=True,
        description=_("The description for the package set at hand."))

    def addSourcePackageNames(spns):
        """Add the passed `SourcePackageName` instances to the package set.

        :param spns: an iterable with `SourcePackageName` instances
        """

    def removeSourcePackageNames(spns):
        """Remove the passed source package names from the package set.

        :param spns: an iterable with `SourcePackageName` instances
        """

    def getDirectSourcePackageNames():
        """Get the source names *directly* associated with this package set.

        This method only returns the source package names that are directly
        associated with the package set at hand i.e. source names related to
        successors of the latter are ignored.
        
        :return: A (potentially empty) result set of `ISourcePackageName`
            instances.
        """

    def getSourcePackageNames():
        """Get all source names associated with this package set.

        This method returns the source package names that are directly
        or indirectly associated with the package set at hand. Indirect
        associations may be defined through package set successors.
        
        :return: A (potentially empty) result set of `ISourcePackageName`
            instances.
        """

    def addDirectSuccessor(package_set):
        """Add the passed package set as a direct successor.

        The passed `Packageset` instance will become a *direct* subset of
        the package set at hand.

        :param package_set: the child `Packageset` instance to include.
        """

    def removeDirectSuccessor(package_set):
        """Remove the passed package set as a director successor.

        If the passed `Packageset` instance is *directly* included by the
        package set at hand it will be removed as a direct successor.

        :param package_set: the direct successor to remove.
        """

    def getPredecessors():
        """Get all package sets that include this one.
        
        Return all package sets that directly or indirectly include this one.
        
        :return: A (potentially empty) result set of `IPackageset`
            instances.
        """

    def getDirectPredecessors():
        """Get all package sets that *directly* include this one.
        
        :return: A (potentially empty) result set of `IPackageset`
            instances.
        """

    def getSuccessors():
        """Get all package sets that are included by this one.
        
        Return all package sets that are directly or indirectly
        included by this one.

        :return: A (potentially empty) result set of `IPackageset`
            instances.
        """

    def getDirectSuccessors():
        """Get all package sets that are *directly* included by this one.
        
        :return: A (potentially empty) result set of `IPackageset`
            instances.
        """


class IPackagesetSet(Interface):
    """An interface for multiple package sets."""
    def new(name, description, owner):
        """Create a new package set.

        :param name: the name of the package set to be created.
        :param description: the description for the package set to be created.
        :param owner: the owner of the package set to be created.

        :return: a newly created `IPackageset`.
        """

    def getByName(name):
        """Return the single package set with the given name (if any).

        :param name: the name of the package set sought.

        :return: An `IPackageset` instance or None.
        """

    def getByOwner(owner):
        """Return the package sets belonging to the given owner (if any).

        :param owner: the owner of the package sets sought.

        :return: A (potentially empty) result set of `IPackageset` instances.
        """
