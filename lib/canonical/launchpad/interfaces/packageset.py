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
    'PackagesetError',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, TextLine

from canonical.launchpad import _
from lp.registry.interfaces.person import IPerson
from canonical.launchpad.validators.name import name_validator
from lazr.restful.fields import Reference


class PackagesetError(Exception):
    '''Raised upon the attempt to add invalid data to a package set.

    Only source package names or other package sets can be added at
    present.
    '''


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

    def add(data):
        """Add source package names or other package sets to this one.

        Any passed `SourcePackageName` or `Packageset` instances will become
        *directly* associated with the package set at hand.

        This function is idempotent in the sense that entities that are
        already directly associated with a package set will be ignored.

        :param data: an iterable with `SourcePackageName` XOR `Packageset`
            instances
        """

    def remove(data):
        """Remove source package names or other package sets from this one.

        Only source package names or package subsets *directly* included by
        this package set can be removed. Any others will be ignored.

        :param data: an iterable with `SourcePackageName` XOR `Packageset`
            instances
        """

    def sources_included_directly():
        """Get the source names *directly* associated with this package set.

        This method only returns the source package names that are directly
        associated with the package set at hand i.e. source names related to
        successors of the latter are ignored.
        
        :return: A (potentially empty) result set of `ISourcePackageName`
            instances.
        """

    def sources_included():
        """Get all source names associated with this package set.

        This method returns the source package names that are directly
        or indirectly associated with the package set at hand. Indirect
        associations may be defined through package set successors.
        
        :return: A (potentially empty) result set of `ISourcePackageName`
            instances.
        """

    def sets_included_by():
        """Get all package sets that include this one.
        
        Return all package sets that directly or indirectly include this one.
        
        :return: A (potentially empty) result set of `IPackageset`
            instances.
        """

    def sets_included_directly_by():
        """Get all package sets that *directly* include this one.
        
        :return: A (potentially empty) result set of `IPackageset`
            instances.
        """

    def sets_included():
        """Get all package sets that are included by this one.
        
        Return all package sets that are directly or indirectly
        included by this one.

        :return: A (potentially empty) result set of `IPackageset`
            instances.
        """

    def sets_included_directly():
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
