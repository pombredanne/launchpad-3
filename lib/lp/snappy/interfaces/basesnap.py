# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base snap interfaces."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "BaseSnapDefaultConflict",
    "CannotDeleteBaseSnap",
    "IBaseSnap",
    "IBaseSnapSet",
    "NoSuchBaseSnap",
    ]

import httplib

from lazr.restful.declarations import (
    call_with,
    collection_default_content,
    error_status,
    export_as_webservice_collection,
    export_as_webservice_entry,
    export_destructor_operation,
    export_factory_operation,
    export_read_operation,
    export_write_operation,
    exported,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import Reference
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import (
    Bool,
    Datetime,
    Dict,
    Int,
    TextLine,
    )

from lp import _
from lp.app.errors import NameLookupFailed
from lp.app.validators.name import name_validator
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.services.fields import (
    ContentNameField,
    PublicPersonChoice,
    Title,
    )


@error_status(httplib.CONFLICT)
class BaseSnapDefaultConflict(Exception):
    """A default base snap already exists."""


class NoSuchBaseSnap(NameLookupFailed):
    """The requested `BaseSnap` does not exist."""

    _message_prefix = "No such base snap"


@error_status(httplib.BAD_REQUEST)
class CannotDeleteBaseSnap(Exception):
    """The base snap cannot be deleted at this time."""


class BaseSnapNameField(ContentNameField):
    """Ensure that `IBaseSnap` has unique names."""

    errormessage = _("%s is already in use by another base snap.")

    @property
    def _content_iface(self):
        """See `UniqueField`."""
        return IBaseSnap

    def _getByName(self, name):
        """See `ContentNameField`."""
        try:
            return getUtility(IBaseSnapSet).getByName(name)
        except NoSuchBaseSnap:
            return None


class IBaseSnapView(Interface):
    """`IBaseSnap` attributes that anyone can view."""

    id = Int(title=_("ID"), required=True, readonly=True)

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    registrant = exported(PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person who registered this base snap.")))

    is_default = exported(Bool(
        title=_("Is default?"), required=True, readonly=True,
        description=_(
            "Whether this base snap indicates the defaults used for snap "
            "builds that do not specify a base snap.")))


class IBaseSnapEditableAttributes(Interface):
    """`IBaseSnap` attributes that can be edited.

    Anyone can view these attributes, but they need launchpad.Edit to change.
    """

    name = exported(BaseSnapNameField(
        title=_("Name"), required=True, readonly=False,
        constraint=name_validator))

    display_name = exported(TextLine(
        title=_("Display name"), required=True, readonly=False))

    title = Title(title=_("Title"), required=True, readonly=True)

    distro_series = exported(Reference(
        IDistroSeries, title=_("Distro series"),
        required=True, readonly=False))

    channels = exported(Dict(
        title=_("Source snap channels"),
        key_type=TextLine(), required=True, readonly=False,
        description=_(
            "A dictionary mapping snap names to channels to use when building "
            "snaps that specify this base snap.")))


class IBaseSnapEdit(Interface):
    """`IBaseSnap` methods that require launchpad.Edit permission."""

    def setDefault(value):
        """Set whether this base snap is the default.

        This is for internal use; the caller should ensure permission to
        edit the base snap and should arrange to remove any existing default
        first.  Most callers should use `IBaseSnapSet.setDefault` instead.

        :param value: True if this base snap should be the default,
            otherwise False.
        """

    @export_destructor_operation()
    @operation_for_version("devel")
    def destroySelf():
        """Delete the specified base snap.

        :raises CannotDeleteBaseSnap: if the base snap cannot be deleted.
        """


class IBaseSnap(IBaseSnapView, IBaseSnapEditableAttributes):
    """A base snap."""

    # XXX cjwatson 2019-01-28 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(as_of="beta")


class IBaseSnapSetEdit(Interface):
    """`IBaseSnapSet` methods that require launchpad.Edit permission."""

    @call_with(registrant=REQUEST_USER)
    @export_factory_operation(
        IBaseSnap, ["name", "display_name", "distro_series", "channels"])
    @operation_for_version("devel")
    def new(registrant, name, display_name, distro_series, channels,
            date_created=None):
        """Create an `IBaseSnap`."""

    @operation_parameters(
        base_snap=Reference(
            title=_("Base snap"), required=True, schema=IBaseSnap))
    @export_write_operation()
    @operation_for_version("devel")
    def setDefault(base_snap):
        """Set the default base snap.

        This will be used to pick the default distro series for snap builds
        that do not specify a base.

        :param base_snap: An `IBaseSnap`, or None to unset the default base
            snap.
        """


class IBaseSnapSet(IBaseSnapSetEdit):
    """Interface representing the set of base snaps."""

    export_as_webservice_collection(IBaseSnap)

    def __iter__():
        """Iterate over `IBaseSnap`s."""

    def __getitem__(name):
        """Return the `IBaseSnap` with this name."""

    @operation_parameters(
        name=TextLine(title=_("Base snap name"), required=True))
    @operation_returns_entry(IBaseSnap)
    @export_read_operation()
    @operation_for_version("devel")
    def getByName(name):
        """Return the `IBaseSnap` with this name.

        :raises NoSuchBaseSnap: if no base snap exists with this name.
        """

    @operation_returns_entry(IBaseSnap)
    @export_read_operation()
    @operation_for_version("devel")
    def getDefault():
        """Get the default base snap.

        This will be used to pick the default distro series for snap builds
        that do not specify a base.
        """

    @collection_default_content()
    def getAll():
        """Return all `IBaseSnap`s."""
