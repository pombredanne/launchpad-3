# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap series interfaces."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ISnapDistroSeries',
    'ISnapDistroSeriesSet',
    'ISnapSeries',
    'ISnapSeriesSet',
    'NoSuchSnapSeries',
    ]

from lazr.restful.declarations import (
    call_with,
    collection_default_content,
    export_as_webservice_collection,
    export_as_webservice_entry,
    export_factory_operation,
    export_read_operation,
    exported,
    operation_for_version,
    operation_parameters,
    operation_returns_collection_of,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import Reference
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import (
    Choice,
    Datetime,
    Int,
    List,
    TextLine,
    )

from lp import _
from lp.app.errors import NameLookupFailed
from lp.app.validators.name import name_validator
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.series import SeriesStatus
from lp.services.fields import (
    ContentNameField,
    PublicPersonChoice,
    Title,
    )


class NoSuchSnapSeries(NameLookupFailed):
    """The requested `SnapSeries` does not exist."""

    _message_prefix = "No such snap series"


class SnapSeriesNameField(ContentNameField):
    """Ensure that `ISnapSeries` has unique names."""

    errormessage = _("%s is already in use by another series.")

    @property
    def _content_iface(self):
        """See `UniqueField`."""
        return ISnapSeries

    def _getByName(self, name):
        """See `ContentNameField`."""
        try:
            return getUtility(ISnapSeriesSet).getByName(name)
        except NoSuchSnapSeries:
            return None


class ISnapSeriesView(Interface):
    """`ISnapSeries` attributes that require launchpad.View permission."""

    id = Int(title=_("ID"), required=True, readonly=True)

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    registrant = exported(PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person who registered this snap package.")))


class ISnapSeriesEditableAttributes(Interface):
    """`ISnapSeries` attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """

    name = exported(SnapSeriesNameField(
        title=_("Name"), required=True, readonly=False,
        constraint=name_validator))

    display_name = exported(TextLine(
        title=_("Display name"), required=True, readonly=False))

    title = Title(title=_("Title"), required=True, readonly=True)

    status = exported(Choice(
        title=_("Status"), required=True, vocabulary=SeriesStatus))

    usable_distro_series = exported(List(
        title=_("Usable distro series"),
        description=_(
            "The distro series that can be used for this snap series."),
        value_type=Reference(schema=IDistroSeries),
        required=True, readonly=False))


class ISnapSeries(ISnapSeriesView, ISnapSeriesEditableAttributes):
    """A series for snap packages in the store."""

    # XXX cjwatson 2016-04-13 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(plural_name="snap_serieses", as_of="beta")


class ISnapDistroSeries(Interface):
    """A snap/distro series link."""

    snap_series = Reference(ISnapSeries, title=_("Snap series"), readonly=True)
    distro_series = Reference(
        IDistroSeries, title=_("Distro series"), readonly=True)

    title = Title(title=_("Title"), required=True, readonly=True)


class ISnapSeriesSetEdit(Interface):
    """`ISnapSeriesSet` methods that require launchpad.Edit permission."""

    @call_with(registrant=REQUEST_USER)
    @export_factory_operation(ISnapSeries, ["name", "display_name", "status"])
    @operation_for_version("devel")
    def new(registrant, name, display_name, status, date_created=None):
        """Create an `ISnapSeries`."""


class ISnapSeriesSet(ISnapSeriesSetEdit):
    """Interface representing the set of snap series."""

    export_as_webservice_collection(ISnapSeries)

    def __iter__():
        """Iterate over `ISnapSeries`."""

    def __getitem__(name):
        """Return the `ISnapSeries` with this name."""

    @operation_parameters(
        name=TextLine(title=_("Snap series name"), required=True))
    @operation_returns_entry(ISnapSeries)
    @export_read_operation()
    @operation_for_version("devel")
    def getByName(name):
        """Return the `ISnapSeries` with this name.

        :raises NoSuchSnapSeries: if no snap series exists with this name.
        """

    @operation_parameters(
        distro_series=Reference(
            IDistroSeries, title=_("Distro series"), required=True))
    @operation_returns_collection_of(ISnapSeries)
    @export_read_operation()
    @operation_for_version("devel")
    def getByDistroSeries(distro_series):
        """Return all `ISnapSeries` usable with this `IDistroSeries`."""

    @collection_default_content()
    def getAll():
        """Return all `ISnapSeries`."""


class ISnapDistroSeriesSet(Interface):
    """Interface representing the set of snap/distro series links."""

    def getByDistroSeries(distro_series):
        """Return all `SnapDistroSeries` for this `IDistroSeries`."""

    def getByBothSeries(snap_series, distro_series):
        """Return a `SnapDistroSeries` for this pair of series, or None."""
