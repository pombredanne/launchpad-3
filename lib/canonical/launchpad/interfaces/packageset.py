# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Packageset interfaces."""

__metaclass__ = type

__all__ = [
    'IPackageset',
    'IPackagesetSet',
    ]

from zope.interface import Interface
from zope.schema import Bool, Datetime, Int, List, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import IHasOwner
from lp.registry.interfaces.person import IPerson
from canonical.launchpad.validators.name import name_validator
from lazr.restful.fields import Reference


class IPackagesetViewOnly(IHasOwner):
    """A read-only interface for package sets."""

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

    def sourcesIncluded(direct_inclusion=False):
        """Get all source names associated with this package set.

        This method returns the source package names that are directly
        or indirectly associated with the package set at hand. Indirect
        associations may be defined through package set successors.

        :param direct_inclusion: if this flag is set to True only sources
            directly included by this package set will be considered.
        :return: A (potentially empty) sequence of `ISourcePackageName`
            instances.
        """

    def setsIncludedBy(direct_inclusion=False):
        """Get all package sets that include this one.

        Return all package sets that directly or indirectly include this one.

        :param direct_inclusion: if this flag is set to True only sets
            directly including this one will be considered.
        :return: A (potentially empty) sequence of `IPackageset` instances.
        """

    def setsIncluded(direct_inclusion=False):
        """Get all package sets that are included by this one.

        Return all package sets that are directly or indirectly
        included by this one.

        :param direct_inclusion: if this flag is set to True only sets
            directly included by this one will be considered.
        :return: A (potentially empty) sequence of `IPackageset` instances.
        """

    def sourcesSharedBy(other_package_set, direct_inclusion=False):
        """Get source package names also included by another package set.

        What source package names does this package set have in common with
        the `other_package_set`?

        :param other_package_set: the other package set
        :param direct_inclusion: if this flag is set to True only directly
            included sources will be considered.
        :return: A (potentially empty) sequence of `ISourcePackageName`
            instances.
        """

    def sourcesNotSharedBy(other_package_set, direct_inclusion=False):
        """Get source package names not included by another package set.

        Which source package names included by this package are *not*
        included by the `other_package_set`?

        :param other_package_set: the other package set
        :param direct_inclusion: if this flag is set to True only directly
            included sources will be considered.
        :return: A (potentially empty) sequence of `ISourcePackageName`
            instances.
        """

    def getSourcesIncluded(direct_inclusion=False):
        """Get all source names associated with this package set.

        This method returns the source package names that are directly
        or indirectly associated with the package set at hand. Indirect
        associations may be defined through package set successors.

        Please note: this method was mainly introduced in order to
        facilitate the listing of source package names via the LP
        web services API. It returns string names as opposed to
        `ISourcePackageName` instances.

        :param direct_inclusion: if this flag is set to True only sources
            directly included by this package set will be considered.
        :return: A (potentially empty) sequence of string source package
            names.
        """

    def getSourcesSharedBy(other_package_set, direct_inclusion=False):
        """Get source package names also included by another package set.

        What source package names does this package set have in common with
        the `other_package_set`?

        Please note: this method was mainly introduced in order to
        facilitate the listing of source package names via the LP
        web services API. It returns string names as opposed to
        `ISourcePackageName` instances.

        :param other_package_set: the other package set
        :param direct_inclusion: if this flag is set to True only directly
            included sources will be considered.
        :return: A (potentially empty) sequence of string source package
            names.
        """

    def getSourcesNotSharedBy(other_package_set, direct_inclusion=False):
        """Get source package names not included by another package set.

        Which source package names included by this package are *not*
        included by the `other_package_set`?

        Please note: this method was mainly introduced in order to
        facilitate the listing of source package names via the LP
        web services API. It returns string names as opposed to
        `ISourcePackageName` instances.

        :param other_package_set: the other package set
        :param direct_inclusion: if this flag is set to True only directly
            included sources will be considered.
        :return: A (potentially empty) sequence of string source package
            names.
        """


class IPackagesetEdit(Interface):
    """A writeable interface for package sets."""

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

    def addSources(names):
        """Add the named source packages to this package set.

        Any passed source package names will become *directly* associated
        with the package set at hand.

        This function is idempotent in the sense that source package names
        that are already directly associated with a package set will be
        ignored.

        Please note: this method was mainly introduced in order to
        facilitate the addition of source package names to package
        sets (by passing in string names) on the LP web services API.

        :param names: an iterable with string source package names
        """

    def removeSources(names):
        """Remove the named source packages from this package set.

        Only source package names *directly* included by this package
        set can be removed. Any others will be ignored.

        Please note: this method was mainly introduced in order to
        facilitate the deletion of source package names from package
        sets (by passing in string names) on the LP web services API.

        :param names: an iterable with string source package names
        """

    def addSubsets(names):
        """Add the named package sets as subsets to this package set.

        Any passed source package names will become *directly* associated
        with the package set at hand.

        This function is idempotent in the sense that package subsets
        that are already directly associated with a package set will be
        ignored.

        Please note: this method was mainly introduced in order to
        facilitate the addition of package subset relations (by passing
        in string names) on the LP web services API.

        :param names: an iterable with string package set names
        """

    def removeSubsets(names):
        """Remove the named package subsets from this package set.

        Only package subsets *directly* included by this package
        set can be removed. Any others will be ignored.

        Please note: this method was mainly introduced in order to
        facilitate the removal of package subset relations (by passing
        in string names) on the LP web services API.

        :param names: an iterable with string package set names
        """


class IPackageset(IPackagesetViewOnly, IPackagesetEdit):
    """An interface for package sets."""


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

        :return: A (potentially empty) sequence of `IPackageset` instances.
        """

    def setsIncludingSource(sourcepackagename, direct_inclusion=False):
        """Get the package sets that include this source package.

        Return all package sets that directly or indirectly include the
        given source package name.

        :param sourcepackagename: the included source package name; can be
            either a string or a `ISourcePackageName`.
        :param direct_inclusion: if this flag is set to True, then only
            package sets that directly include this source package name will
            be considered.

        :raises NoSuchSourcePackageName: if a source package with the given
            name cannot be found.
        :return: A (potentially empty) sequence of `IPackageset` instances.
        """
