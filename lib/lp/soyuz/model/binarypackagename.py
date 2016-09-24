# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BinaryPackageName',
    'BinaryPackageNameSet',
    ]

from sqlobject import (
    SQLObjectNotFound,
    StringCol,
    )
from storm.expr import Join
from storm.store import EmptyResultSet
from zope.interface import implementer

from lp.app.errors import NotFoundError
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import SQLBase
from lp.services.helpers import ensure_unicode
from lp.soyuz.interfaces.binarypackagename import (
    IBinaryPackageName,
    IBinaryPackageNameSet,
    )
from lp.soyuz.interfaces.publishing import active_publishing_status


@implementer(IBinaryPackageName)
class BinaryPackageName(SQLBase):
    _table = 'BinaryPackageName'
    name = StringCol(dbName='name', notNull=True, unique=True,
                     alternateID=True)

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<BinaryPackageName at %X name=%r>" % (id(self), self.name)


@implementer(IBinaryPackageNameSet)
class BinaryPackageNameSet:

    def __getitem__(self, name):
        """See `IBinaryPackageNameSet`."""
        try:
            return BinaryPackageName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def getAll(self):
        """See `IBinaryPackageNameSet`."""
        return BinaryPackageName.select()

    def queryByName(self, name):
        return IStore(BinaryPackageName).find(
            BinaryPackageName, name=ensure_unicode(name)).one()

    def new(self, name):
        return BinaryPackageName(name=ensure_unicode(name))

    def ensure(self, name):
        """Ensure that the given BinaryPackageName exists, creating it
        if necessary.

        Returns the BinaryPackageName
        """
        name = ensure_unicode(name)
        try:
            return self[name]
        except NotFoundError:
            return self.new(name)

    getOrCreateByName = ensure

    def getNotNewByNames(self, name_ids, distroseries, archive_ids):
        """See `IBinaryPackageNameSet`."""
        # Circular imports.
        from lp.soyuz.model.distroarchseries import DistroArchSeries
        from lp.soyuz.model.publishing import BinaryPackagePublishingHistory

        if len(name_ids) == 0:
            return EmptyResultSet()

        return IStore(BinaryPackagePublishingHistory).using(
            BinaryPackagePublishingHistory,
            Join(BinaryPackageName,
                BinaryPackagePublishingHistory.binarypackagenameID ==
                BinaryPackageName.id),
            Join(DistroArchSeries,
                BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id)
            ).find(
                BinaryPackageName,
                DistroArchSeries.distroseries == distroseries,
                BinaryPackagePublishingHistory.status.is_in(
                    active_publishing_status),
                BinaryPackagePublishingHistory.archiveID.is_in(archive_ids),
                BinaryPackagePublishingHistory.binarypackagenameID.is_in(
                    name_ids)).config(distinct=True)
