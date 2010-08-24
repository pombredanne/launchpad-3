# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface classes for a difference between two distribution series."""

__metaclass__ = type


__all__ = [
    'IDistroSeriesDifference',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Choice,
    Int,
    Text,
    )

from canonical.launchpad import _
from lp.registry.enum import DistroSeriesDifferenceStatus
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.soyuz.interfaces.publishing import ISourcePackagePublishingHistory


class IDistroSeriesDifference(Interface):
    """An interface for a package difference between two distroseries."""

    id = Int(title=_('ID'), required=True, readonly=True)

    derived_series = Reference(
        IDistroSeries, title=_("Derived series"), required=True,
        readonly=True, description=_(
            "The distribution series which, together with its parent, "
            "identifies the two series with the difference."))

    source_package = Reference(
        ISourcePackagePublishingHistory,
        title=_("Source package"), required=False,
        readonly=True, description=_(
            "The package in this distribution series."))

    parent_source_package = Reference(
        ISourcePackagePublishingHistory,
        title=_("Parent source package"), required=False,
        readonly=True, description=_(
            "The package in the parent distribution series."))

    comment = Text(
        title=_('Custom information about the current status of this '
                'difference'), required=False, readonly=False)

    status = Choice(
        title=_('Distro series difference status.'),
        description=_('The current status of this difference.'),
        vocabulary=DistroSeriesDifferenceStatus,
        required=True, readonly=False)


class IDistroSeriesDifferenceSource(Interface):
    """A utility of this interface can be used to create differences."""

    def new(derived_series, source_package=None, parent_source_package=None,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION):
        """Create an `IDistroSeriesDifference`.

        :param derived_series: The distribution series which was derived
            from a parent. If a series without a parent is passed an
            exception is raised.
        :type derived_series: `IDistroSeries`.
        :param source_package: A source package in the derived series.
        :type source_package: `ISourcePackagePublishingHistory`.
        :param parent_source_package: A source package in the parent series.
        :type source_package: `ISourcePackagePublishingHistory`.
        :param status: The current status of this difference.
        :type status: `DistorSeriesDifferenceStatus`.
        """

