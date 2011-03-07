# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface classes for a difference between two distribution series."""

__metaclass__ = type


__all__ = [
    'IDistroSeriesDifference',
    'IDistroSeriesDifferencePublic',
    'IDistroSeriesDifferenceEdit',
    'IDistroSeriesDifferenceSource',
    ]

from lazr.restful.declarations import (
    call_with,
    export_as_webservice_entry,
    export_write_operation,
    exported,
    operation_parameters,
    REQUEST_USER,
    )
from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Bool,
    Choice,
    Int,
    Text,
    TextLine,
    )

from canonical.launchpad import _
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.registry.interfaces.role import IHasOwner
from lp.soyuz.interfaces.packagediff import IPackageDiff
from lp.soyuz.interfaces.publishing import ISourcePackagePublishingHistory


class IDistroSeriesDifferencePublic(IHasOwner, Interface):
    """The public interface for distro series differences."""

    id = Int(title=_('ID'), required=True, readonly=True)

    derived_series = exported(Reference(
        IDistroSeries, title=_("Derived series"), required=True,
        readonly=True, description=_(
            "The distribution series which, together with its parent, "
            "identifies the two series with the difference.")))

    source_package_name = Reference(
        ISourcePackageName,
        title=_("Source package name"), required=True, readonly=True,
        description=_(
            "The package with a difference between the derived series "
            "and its parent."))

    package_diff = Reference(
        IPackageDiff, title=_("Package diff"), required=False,
        readonly=True, description=_(
            "The most recently generated package diff from the base to the "
            "derived version."))

    package_diff_url = exported(TextLine(
        title=_("Package diff url"), readonly=True, required=False,
        description=_(
            "The url for the diff between the base version and the "
            "derived version.")))

    parent_package_diff = Reference(
        IPackageDiff, title=_("Parent package diff"), required=False,
        readonly=True, description=_(
            "The most recently generated package diff from the base to the "
            "parent version."))

    parent_package_diff_url = exported(TextLine(
        title=_("Parent package diff url"), readonly=True, required=False,
        description=_(
            "The url for the diff between the base version and the "
            "parent version.")))

    status = Choice(
        title=_('Distro series difference status.'),
        description=_('The current status of this difference.'),
        vocabulary=DistroSeriesDifferenceStatus,
        required=True, readonly=True)

    difference_type = Choice(
        title=_('Difference type'),
        description=_('The type of difference for this package.'),
        vocabulary=DistroSeriesDifferenceType,
        required=True, readonly=True)

    source_pub = Reference(
        ISourcePackagePublishingHistory,
        title=_("Derived source pub"), readonly=True,
        description=_(
            "The most recent published version in the derived series."))

    source_version = TextLine(
        title=_("Source version"), readonly=True,
        description=_(
            "The version of the most recent source publishing in the "
            "derived series."))

    parent_source_pub = Reference(
        ISourcePackagePublishingHistory,
        title=_("Parent source pub"), readonly=True,
        description=_(
            "The most recent published version in the parent series."))

    parent_source_version = TextLine(
        title=_("Parent source version"), readonly=True,
        description=_(
            "The version of the most recent source publishing in the "
            "parent series."))

    base_version = TextLine(
        title=_("Base version"), readonly=True,
        description=_(
            "The common base version of the package for differences "
            "with different versions in the parent and derived series."))

    base_source_pub = Reference(
        ISourcePackagePublishingHistory,
        title=_("Base source pub"), readonly=True,
        description=_(
            "The common base version published in the derived series."))

    owner = Reference(
        IPerson, title=_("Owning team of the derived series"), readonly=True,
        description=_(
            "This attribute mirrors the owner of the derived series."))

    title = TextLine(
        title=_("Title"), readonly=True, required=False, description=_(
            "A human-readable name describing this difference."))

    def update():
        """Checks that difference type and status matches current publishings.

        If the record is updated, a relevant comment is added.

        If there is no longer a difference (ie. the versions are
        the same) then the status is updated to RESOLVED.

        :return: True if the record was updated, False otherwise.
        """

    def getComments():
        """Return a result set of the comments for this difference."""


class IDistroSeriesDifferenceEdit(Interface):
    """Difference attributes requiring launchpad.Edit."""

    @call_with(commenter=REQUEST_USER)
    @operation_parameters(
        comment=Text(title=_("Comment text"), required=True))
    @export_write_operation()
    def addComment(commenter, comment):
        """Add a comment on this difference."""

    @operation_parameters(
        all=Bool(title=_("All"), required=False))
    @export_write_operation()
    def blacklist(all=False):
        """Blacklist this version or all versions of this source package.

        :param all: indicates whether all versions of this package should
            be blacklisted or just the current (default).
        """

    @export_write_operation()
    def unblacklist():
        """Removes this difference from the blacklist.

        The status will be updated based on the versions.
        """

    @call_with(requestor=REQUEST_USER)
    @export_write_operation()
    def requestPackageDiffs(requestor):
        """Requests IPackageDiffs for the derived and parent version.

        :raises DistroSeriesDifferenceError: When package diffs
            cannot be requested.
        """


class IDistroSeriesDifference(IDistroSeriesDifferencePublic,
                              IDistroSeriesDifferenceEdit):
    """An interface for a package difference between two distroseries."""
    export_as_webservice_entry()


class IDistroSeriesDifferenceSource(Interface):
    """A utility of this interface can be used to create differences."""

    def new(derived_series, source_package_name):
        """Create an `IDistroSeriesDifference`.

        :param derived_series: The distribution series which was derived
            from a parent. If a series without a parent is passed an
            exception is raised.
        :type derived_series: `IDistroSeries`.
        :param source_package_name: A source package name identifying the
            package with a difference.
        :type source_package_name: `ISourcePackageName`.
        :raises NotADerivedSeriesError: When the passed distro series
            is not a derived series.
        :return: A new `DistroSeriesDifference` object.
        """

    def getForDistroSeries(
        distro_series,
        difference_type=DistroSeriesDifferenceType.DIFFERENT_VERSIONS,
        source_package_name_filter=None,
        status=None):
        """Return differences for the derived distro series.

        :param distro_series: The derived distribution series which is to be
            searched for differences.
        :type distro_series: `IDistroSeries`.
        :param difference_type: The type of difference to include in the
            results.
        :type difference_type: `DistroSeriesDifferenceType`.
        :param source_package_name_filter: Package source name filter.
        :type source_package_name_filter: unicode.
        :param status: Only differences matching the status(es) will be
            included.
        :type status: `DistroSeriesDifferenceStatus`.
        :return: A result set of differences.
        """

    def getByDistroSeriesAndName(distro_series, source_package_name):
        """Returns a single difference matching the series and name.

        :param distro_series: The derived distribution series which is to be
            searched for differences.
        :type distro_series: `IDistroSeries`.
        :param source_package_name: The name of the package difference.
        :type source_package_name: unicode.
        """
