# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of `ICanHasDefaultGitRepository`."""

__metaclass__ = type
# Don't export anything -- anything you need from this module you can get by
# adapting another object.
__all__ = []

from lazr.enum import (
    EnumeratedType,
    Item,
    )
from zope.component import (
    adapts,
    getUtility,
    )
from zope.interface import implements

from lp.code.interfaces.defaultgit import ICanHasDefaultGitRepository
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.persondistributionsourcepackage import (
    IPersonDistributionSourcePackage,
    )
from lp.registry.interfaces.personproduct import IPersonProduct
from lp.registry.interfaces.product import IProduct


class DefaultGitRepositoryOrder(EnumeratedType):
    """An enum used only for ordering."""

    PROJECT = Item("Project shortcut")
    DISTRIBUTION_SOURCE_PACKAGE = Item("Distribution source package shortcut")
    OWNER_PROJECT = Item("Owner's default for a project")
    OWNER_DISTRIBUTION_SOURCE_PACKAGE = Item(
        "Owner's default for a distribution source package")


class BaseDefaultGitRepository:
    """Provides the common sorting algorithm."""

    def __cmp__(self, other):
        if not ICanHasDefaultGitRepository.providedBy(other):
            raise AssertionError("Can't compare with: %r" % other)
        return cmp(self.sort_order, other.sort_order)

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.context == other.context)

    def __ne__(self, other):
        return not self == other


class ProjectDefaultGitRepository(BaseDefaultGitRepository):
    """Implement a default Git repository for a project."""

    adapts(IProduct)
    implements(ICanHasDefaultGitRepository)

    sort_order = DefaultGitRepositoryOrder.PROJECT

    def __init__(self, project):
        self.context = project

    @property
    def project(self):
        return self.context

    def __cmp__(self, other):
        result = super(ProjectDefaultGitRepository, self).__cmp__(other)
        if result != 0:
            return result
        else:
            return cmp(self.project.name, other.project.name)

    @property
    def repository(self):
        """See `ICanHasDefaultGitRepository`."""
        return getUtility(IGitRepositorySet).getDefaultRepository(self.context)

    def setRepository(self, repository):
        """See `ICanHasDefaultGitRepository`."""
        return getUtility(IGitRepositorySet).setDefaultRepository(
            self.context, repository)

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return self.project.name


class PackageDefaultGitRepository(BaseDefaultGitRepository):
    """Implement a default Git repository for a distribution source package."""

    adapts(IDistributionSourcePackage)
    implements(ICanHasDefaultGitRepository)

    sort_order = DefaultGitRepositoryOrder.DISTRIBUTION_SOURCE_PACKAGE

    def __init__(self, distro_source_package):
        self.context = distro_source_package

    @property
    def distro_source_package(self):
        return self.context

    @property
    def distribution(self):
        return self.context.distribution

    @property
    def sourcepackagename(self):
        return self.context.sourcepackagename

    def __cmp__(self, other):
        result = super(PackageDefaultGitRepository, self).__cmp__(other)
        if result != 0:
            return result
        else:
            my_names = (self.distribution.name, self.sourcepackagename.name)
            other_names = (
                other.distribution.name, other.sourcepackagename.name)
            return cmp(my_names, other_names)

    @property
    def repository(self):
        """See `ICanHasDefaultGitRepository`."""
        return getUtility(IGitRepositorySet).getDefaultRepository(self.context)

    def setRepository(self, repository):
        """See `ICanHasDefaultGitRepository`."""
        return getUtility(IGitRepositorySet).setDefaultRepository(
            self.context, repository)

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return "%s/+source/%s" % (
            self.distribution.name, self.sourcepackagename.name)


class OwnerProjectDefaultGitRepository(BaseDefaultGitRepository):
    """Implement an owner's default Git repository for a project."""

    adapts(IPersonProduct)
    implements(ICanHasDefaultGitRepository)

    sort_order = DefaultGitRepositoryOrder.OWNER_PROJECT

    def __init__(self, person_project):
        self.context = person_project

    @property
    def person_project(self):
        return self.context

    @property
    def person(self):
        return self.context.person

    @property
    def project(self):
        return self.context.product

    def __cmp__(self, other):
        result = super(OwnerProjectDefaultGitRepository, self).__cmp__(other)
        if result != 0:
            return result
        else:
            my_names = (self.person.name, self.project.name)
            other_names = (other.person.name, other.project.name)
            return cmp(my_names, other_names)

    @property
    def repository(self):
        """See `ICanHasDefaultGitRepository`."""
        return getUtility(IGitRepositorySet).getDefaultRepositoryForOwner(
            self.person, self.project)

    def setRepository(self, repository):
        """See `ICanHasDefaultGitRepository`."""
        return getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
            self.person, self.project, repository)

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return "~%s/%s" % (self.person.name, self.project.name)


class OwnerPackageDefaultGitRepository(BaseDefaultGitRepository):
    """Implement an owner's default Git repository for a distribution source
    package."""

    adapts(IPersonDistributionSourcePackage)
    implements(ICanHasDefaultGitRepository)

    sort_order = DefaultGitRepositoryOrder.OWNER_DISTRIBUTION_SOURCE_PACKAGE

    def __init__(self, person_distro_source_package):
        self.context = person_distro_source_package

    @property
    def person_distro_source_package(self):
        return self.context

    @property
    def person(self):
        return self.context.person

    @property
    def distro_source_package(self):
        return self.context.distro_source_package

    @property
    def distribution(self):
        return self.distro_source_package.distribution

    @property
    def sourcepackagename(self):
        return self.distro_source_package.sourcepackagename

    def __cmp__(self, other):
        result = super(OwnerPackageDefaultGitRepository, self).__cmp__(other)
        if result != 0:
            return result
        else:
            my_names = (
                self.person.name, self.distribution.name,
                self.sourcepackagename.name)
            other_names = (
                other.person.name, other.distribution.name,
                other.sourcepackagename.name)
            return cmp(my_names, other_names)

    @property
    def repository(self):
        """See `ICanHasDefaultGitRepository`."""
        return getUtility(IGitRepositorySet).getDefaultRepositoryForOwner(
            self.person, self.distro_source_package)

    def setRepository(self, repository):
        """See `ICanHasDefaultGitRepository`."""
        return getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
            self.person, self.distro_source_package, repository)

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return "~%s/%s/+source/%s" % (
            self.person.name, self.distribution.name,
            self.sourcepackagename.name)
