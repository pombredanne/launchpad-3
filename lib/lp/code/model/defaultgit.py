# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of `ICanHasDefaultGitRepository`."""

__metaclass__ = type
# Don't export anything -- anything you need from this module you can get by
# adapting another object.
__all__ = []

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

    sort_order = 0

    def __init__(self, project):
        self.context = project

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return self.context.name


class PackageDefaultGitRepository(BaseDefaultGitRepository):
    """Implement a default Git repository for a distribution source package."""

    adapts(IDistributionSourcePackage)
    implements(ICanHasDefaultGitRepository)

    sort_order = 0

    def __init__(self, distro_source_package):
        self.context = distro_source_package

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

    sort_order = 1

    def __init__(self, person_project):
        self.context = person_project

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        return "~%s/%s" % (self.context.person.name, self.context.product.name)


class OwnerPackageDefaultGitRepository(BaseDefaultGitRepository):
    """Implement an owner's default Git repository for a distribution source
    package."""

    adapts(IPersonDistributionSourcePackage)
    implements(ICanHasDefaultGitRepository)

    sort_order = 1

    def __init__(self, person_distro_source_package):
        self.context = person_distro_source_package

    @property
    def path(self):
        """See `ICanHasDefaultGitRepository`."""
        dsp = self.context.distro_source_package
        return "~%s/%s/+source/%s" % (
            self.context.person.name, dsp.distribution.name,
            dsp.sourcepackagename.name)
