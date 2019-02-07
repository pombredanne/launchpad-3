# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base snaps."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "BaseSnap",
    ]

import pytz
from storm.locals import (
    Bool,
    DateTime,
    Int,
    JSON,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.services.database.constants import DEFAULT
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.snappy.interfaces.basesnap import (
    CannotDeleteBaseSnap,
    IBaseSnap,
    IBaseSnapSet,
    NoSuchBaseSnap,
    )


@implementer(IBaseSnap)
class BaseSnap(Storm):
    """See `IBaseSnap`."""

    __storm_table__ = "BaseSnap"

    id = Int(primary=True)

    date_created = DateTime(
        name="date_created", tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name="registrant", allow_none=False)
    registrant = Reference(registrant_id, "Person.id")

    name = Unicode(name="name", allow_none=False)

    display_name = Unicode(name="display_name", allow_none=False)

    distro_series_id = Int(name="distro_series", allow_none=False)
    distro_series = Reference(distro_series_id, "DistroSeries.id")

    channels = JSON(name="channels", allow_none=False)

    is_default = Bool(name="is_default", allow_none=False)

    def __init__(self, registrant, name, display_name, distro_series, channels,
                 date_created=DEFAULT):
        super(BaseSnap, self).__init__()
        self.registrant = registrant
        self.name = name
        self.display_name = display_name
        self.distro_series = distro_series
        self.channels = channels
        self.date_created = date_created
        self.is_default = False

    @property
    def title(self):
        """See `IBaseSnap`."""
        return self.display_name

    def destroySelf(self):
        """See `IBaseSnap`."""
        # Guard against unfortunate accidents.
        if self.is_default:
            raise CannotDeleteBaseSnap("Cannot delete the default base snap.")
        Store.of(self).remove(self)


@implementer(IBaseSnapSet)
class BaseSnapSet:
    """See `IBaseSnapSet`."""

    def new(self, registrant, name, display_name, distro_series, channels,
            date_created=DEFAULT):
        """See `IBaseSnapSet`."""
        store = IMasterStore(BaseSnap)
        base_snap = BaseSnap(
            registrant, name, display_name, distro_series, channels,
            date_created=date_created)
        store.add(base_snap)
        return base_snap

    def __iter__(self):
        """See `IBaseSnapSet`."""
        return iter(self.getAll())

    def __getitem__(self, name):
        """See `IBaseSnapSet`."""
        return self.getByName(name)

    def getByName(self, name):
        """See `IBaseSnapSet`."""
        base_snap = IStore(BaseSnap).find(
            BaseSnap, BaseSnap.name == name).one()
        if base_snap is None:
            raise NoSuchBaseSnap(name)
        return base_snap

    def getDefault(self):
        """See `IBaseSnapSet`."""
        return IStore(BaseSnap).find(
            BaseSnap, BaseSnap.is_default == True).one()

    def setDefault(self, base_snap):
        """See `IBaseSnapSet`."""
        previous = self.getDefault()
        if previous != base_snap:
            # We can safely remove the security proxy here, because the
            # default base snap is logically a property of the set even
            # though it is stored on the base snap.
            if previous is not None:
                removeSecurityProxy(previous).is_default = False
            if base_snap is not None:
                removeSecurityProxy(base_snap).is_default = True

    def getAll(self):
        """See `IBaseSnapSet`."""
        return IStore(BaseSnap).find(BaseSnap).order_by(BaseSnap.name)
