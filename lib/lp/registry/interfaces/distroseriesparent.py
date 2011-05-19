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
    Bool,
    Choice,
    Int,
    )

from canonical.launchpad import _
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.pocket import PackagePublishingPocket


class IDistroSeriesParent(Interface):
    """`DistroSeriesParent` interface."""

    id = Int(title=_('ID'), required=True, readonly=True)

    derived_series = Reference(
        IDistroSeries, title=_("Derived Series"), required=True,
        description=_("The derived distribution series."))

    parent_series = Reference(
        IDistroSeries, title=_("Parent Series"), required=True,
        description=_("The parent distribution series."))

    initialized = Bool(
        title=_("Initialized"), required=True,
        description=_(
            "Whether or not the derived_series has been populated with "
            "packages from its parent_series."))

    is_overlay = Bool(
        title=_("Is this relationship an overlay?"), required=True,
        default=False)

    pocket = Choice(
        title=_("The pocket for this overlay"), required=False,
        vocabulary=PackagePublishingPocket)

    component = Choice(
        title=_("The component for this overlay"), required=False,
        vocabulary='Component')


class IDistroSeriesParentSet(Interface):
    """`DistroSeriesParentSet` interface."""

    def new(derived_series, parent_series, initialized, is_overlay=False,
            pocket=None, component=None):
        """Create a new `DistroSeriesParent`."""

    def getByDerivedSeries(derived_series):
        """Get the `DistroSeriesParent` by derived series.

        :param derived_series: An `IDistroseries`
        """

    def getByParentSeries(parent_series):
        """Get the `DistroSeriesParent` by parent series.

        :param parent_series: An `IDistroseries`
        """
