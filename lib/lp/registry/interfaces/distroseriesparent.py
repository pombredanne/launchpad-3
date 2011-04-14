# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""DistroSeriesParent interface."""

__metaclass__ = type

__all__ = [
    'IDistroSeriesParent',
    'IDistroSeriesParentSet',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Int,
    Bool,
    )

from canonical.launchpad import _
from lp.registry.interfaces.distribution import IDistroseries


class IDistroSeriesParent(Interface):
    """`DistroSeriesParent` interface."""

    id = Int(title=_('ID'), required=True, readonly=True)

    derived_series = Reference(
        IDistroseries, title=_("Derived Series"), required=True,
        description=_("The derived distribution series."))

    parent_series = Reference(
        IDistroseries, title=_("Parent Series"), required=True,
        description=_("The parent distribution series."))

    initialized = Bool(
        title=_("Initialized"), required=True,
        description=_(
            "Whether or not the derived_series has been populated with "
            "packages from its parent_series."))


class IPublisherConfigSet(Interface):
    """`DistroSeriesParentSet` interface."""

    def new(derived_series, parent_series, initialized):
        """Create a new `DistroSeriesParent`."""

    def getByDerivedSeries(derived_series):
        """Get the `DistroSeriesParent` by derived series.

        :param derived_series: An `IDistroseries`
        """

    def getByParentSeries(parent_series):
        """Get the `DistroSeriesParent` by parent series.

        :param parent_series: An `IDistroseries`
        """
