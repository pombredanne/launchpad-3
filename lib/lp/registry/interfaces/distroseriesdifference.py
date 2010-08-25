# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface classes for a difference between two distribution series."""

__metaclass__ = type


__all__ = [
    'IDistroSeriesDifference',
    'IDistroSeriesDifferenceSource',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Choice,
    Int,
    Text,
    )

from canonical.launchpad import _
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.soyuz.interfaces.packagediff import IPackageDiff
from lp.soyuz.interfaces.publishing import ISourcePackagePublishingHistory


class IDistroSeriesDifference(Interface):
    """An interface for a package difference between two distroseries."""

    id = Int(title=_('ID'), required=True, readonly=True)

    derived_series = Reference(
        IDistroSeries, title=_("Derived series"), required=True,
        readonly=True, description=_(
            "The distribution series which, together with its parent, "
            "identifies the two series with the difference."))

    source_package_name = Reference(
        ISourcePackageName,
        title=_("Source package name"), required=True, readonly=True,
        description=_(
            "The package with a difference between the derived series "
            "and its parent."))

    last_package_diff = Reference(
        IPackageDiff, title=_("Last package diff"), required=False,
        readonly=True, description=_(
            "The most recently generated package diff for this difference."))

    activity_log = Text(
        title=_('A log of activity and comments for this difference'),
        required=False, readonly=False)

    status = Choice(
        title=_('Distro series difference status.'),
        description=_('The current status of this difference.'),
        vocabulary=DistroSeriesDifferenceStatus,
        required=True, readonly=False)

    difference_type = Choice(
        title=_('Difference type'),
        description=_('The type of difference for this package.'),
        vocabulary=DistroSeriesDifferenceType,
        required=True, readonly=False)

    source_pub = Reference(
        ISourcePackagePublishingHistory,
        title=_("Derived source pub"), readonly=True,
        description=_(
            "The most recent published version in the derived series."))

    parent_source_pub = Reference(
        ISourcePackagePublishingHistory,
        title=_("Parent source pub"), readonly=True,
        description=_(
            "The most recent published version in the parent series."))

    def appendActivityLog(message):
        """Add a message to the activity log.

        :param message: The message to be appended to the activity log.
        """


class IDistroSeriesDifferenceSource(Interface):
    """A utility of this interface can be used to create differences."""

    def new(derived_series, source_package_name, difference_type,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION):
        """Create an `IDistroSeriesDifference`.

        :param derived_series: The distribution series which was derived
            from a parent. If a series without a parent is passed an
            exception is raised.
        :type derived_series: `IDistroSeries`.
        :param source_package_name: A source package name identifying the
            package with a difference.
        :type source_package_name: `ISourcePackageName`.
        :param difference_type: Indicates the type of difference represented
            by this record.
        :type difference_type: `DistroSeriesDifferenceType`.
        :param status: The current status of this difference.
        :type status: `DistorSeriesDifferenceStatus`.
        :raises NotADerivedSeriesError: When the passed distro series
            is not a derived series.
        :return: A new `DistroSeriesDifference` object.
        """

