# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snappy series interfaces."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ISnappyDistroSeries',
    'ISnappyDistroSeriesSet',
    'ISnappySeries',
    'ISnappySeriesSet',
    'NoSuchSnappySeries',
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


class NoSuchSnappySeries(NameLookupFailed):
    """The requested `SnappySeries` does not exist."""

    _message_prefix = "No such snappy series"


class SnappySeriesNameField(ContentNameField):
    """Ensure that `ISnappySeries` has unique names."""

    errormessage = _("%s is already in use by another series.")

    @property
    def _content_iface(self):
        """See `UniqueField`."""
        return ISnappySeries

    def _getByName(self, name):
        """See `ContentNameField`."""
        try:
            return getUtility(ISnappySeriesSet).getByName(name)
        except NoSuchSnappySeries:
            return None


class ISnappySeriesView(Interface):
    """`ISnappySeries` attributes that anyone can view."""

    id = Int(title=_("ID"), required=True, readonly=True)

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    registrant = exported(PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person who registered this snap package.")))


class ISnappySeriesEditableAttributes(Interface):
    """`ISnappySeries` attributes that can be edited.

    Anyone can view these attributes, but they need launchpad.Edit to change.
    """

    name = exported(SnappySeriesNameField(
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
            "The distro series that can be used for this snappy series."),
        value_type=Reference(schema=IDistroSeries),
        required=True, readonly=False))


class ISnappySeries(ISnappySeriesView, ISnappySeriesEditableAttributes):
    """A series for snap packages in the store."""

    # XXX cjwatson 2016-04-13 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(plural_name="snappy_serieses", as_of="beta")


class ISnappyDistroSeries(Interface):
    """A snappy/distro series link."""

    snappy_series = Reference(
        ISnappySeries, title=_("Snappy series"), readonly=True)
    distro_series = Reference(
        IDistroSeries, title=_("Distro series"), readonly=True)

    title = Title(title=_("Title"), required=True, readonly=True)


class ISnappySeriesSetEdit(Interface):
    """`ISnappySeriesSet` methods that require launchpad.Edit permission."""

    @call_with(registrant=REQUEST_USER)
    @export_factory_operation(
        ISnappySeries, ["name", "display_name", "status"])
    @operation_for_version("devel")
    def new(registrant, name, display_name, status, date_created=None):
        """Create an `ISnappySeries`."""


class ISnappySeriesSet(ISnappySeriesSetEdit):
    """Interface representing the set of snappy series."""

    export_as_webservice_collection(ISnappySeries)

    def __iter__():
        """Iterate over `ISnappySeries`."""

    def __getitem__(name):
        """Return the `ISnappySeries` with this name."""

    @operation_parameters(
        name=TextLine(title=_("Snappy series name"), required=True))
    @operation_returns_entry(ISnappySeries)
    @export_read_operation()
    @operation_for_version("devel")
    def getByName(name):
        """Return the `ISnappySeries` with this name.

        :raises NoSuchSnappySeries: if no snappy series exists with this name.
        """

    @operation_parameters(
        distro_series=Reference(
            IDistroSeries, title=_("Distro series"), required=True))
    @operation_returns_collection_of(ISnappySeries)
    @export_read_operation()
    @operation_for_version("devel")
    def getByDistroSeries(distro_series):
        """Return all `ISnappySeries` usable with this `IDistroSeries`."""

    @collection_default_content()
    def getAll():
        """Return all `ISnappySeries`."""


class ISnappyDistroSeriesSet(Interface):
    """Interface representing the set of snappy/distro series links."""

    def getByDistroSeries(distro_series):
        """Return all `SnappyDistroSeries` for this `IDistroSeries`."""

    def getByBothSeries(snappy_series, distro_series):
        """Return a `SnappyDistroSeries` for this pair of series, or None."""

    def getAll():
        """Return all `SnappyDistroSeries`."""
