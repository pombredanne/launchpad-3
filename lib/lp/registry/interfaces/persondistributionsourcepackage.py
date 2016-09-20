# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A person's view on a source package in a distribution."""

__metaclass__ = type
__all__ = [
    'IPersonDistributionSourcePackage',
    'IPersonDistributionSourcePackageFactory',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import TextLine

from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )


class IPersonDistributionSourcePackage(Interface):
    """A person's view on a source package in a distribution."""

    person = Reference(IPerson)
    distro_source_package = Reference(IDistributionSourcePackage)
    displayname = TextLine()


class IPersonDistributionSourcePackageFactory(Interface):
    """Creates `IPersonDistributionSourcePackage`s."""

    def create(person, distro_source_package):
        """Create and return an `IPersonDistributionSourcePackage`."""
