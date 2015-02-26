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
from zope.component import adapts
from zope.interface import implements

from lp.code.interfaces.defaultgit import ICanHasDefaultGitRepository
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

    def __cmp__(self, other):
        result = super(ProjectDefaultGitRepository, self).__cmp__(other)
        if result != 0:
            return result
        else:
            return cmp(self.context.name, other.context.name)

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return self.context.name


class PackageDefaultGitRepository(BaseDefaultGitRepository):
    """Implement a default Git repository for a distribution source package."""

    adapts(IDistributionSourcePackage)
    implements(ICanHasDefaultGitRepository)

    sort_order = DefaultGitRepositoryOrder.DISTRIBUTION_SOURCE_PACKAGE

    def __init__(self, distro_source_package):
        self.context = distro_source_package

    def __cmp__(self, other):
        result = super(PackageDefaultGitRepository, self).__cmp__(other)
        if result != 0:
            return result
        else:
            my_names = (
                self.context.distribution.name,
                self.context.sourcepackagename.name)
            other_names = (
                other.context.distribution.name,
                other.context.sourcepackagename.name)
            return cmp(my_names, other_names)

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return "%s/+source/%s" % (
            self.context.distribution.name,
            self.context.sourcepackagename.name)


class OwnerProjectDefaultGitRepository(BaseDefaultGitRepository):
    """Implement an owner's default Git repository for a project."""

    adapts(IPersonProduct)
    implements(ICanHasDefaultGitRepository)

    sort_order = DefaultGitRepositoryOrder.OWNER_PROJECT

    def __init__(self, person_project):
        self.context = person_project

    def __cmp__(self, other):
        result = super(OwnerProjectDefaultGitRepository, self).__cmp__(other)
        if result != 0:
            return result
        else:
            my_names = (self.context.person.name, self.context.product.name)
            other_names = (
                other.context.person.name, other.context.product.name)
            return cmp(my_names, other_names)

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return "~%s/%s" % (self.context.person.name, self.context.product.name)


class OwnerPackageDefaultGitRepository(BaseDefaultGitRepository):
    """Implement an owner's default Git repository for a distribution source
    package."""

    adapts(IPersonDistributionSourcePackage)
    implements(ICanHasDefaultGitRepository)

    sort_order = DefaultGitRepositoryOrder.OWNER_DISTRIBUTION_SOURCE_PACKAGE

    def __init__(self, person_distro_source_package):
        self.context = person_distro_source_package

    def __cmp__(self, other):
        result = super(OwnerPackageDefaultGitRepository, self).__cmp__(other)
        if result != 0:
            return result
        else:
            my_dsp = self.context.distro_source_package
            other_dsp = other.context.distro_source_package
            my_names = (
                self.context.person.name, my_dsp.distribution.name,
                my_dsp.sourcepackagename.name)
            other_names = (
                other.context.person.name, other_dsp.distribution.name,
                other_dsp.sourcepackagename.name)
            return cmp(my_names, other_names)

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        dsp = self.context.distro_source_package
        return "~%s/%s/+source/%s" % (
            self.context.person.name, dsp.distribution.name,
            dsp.sourcepackagename.name)
