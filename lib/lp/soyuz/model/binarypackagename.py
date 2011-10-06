# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'BinaryPackageName',
    'BinaryPackageNameSet',
    'BinaryPackageNameVocabulary',
    'getBinaryPackageDescriptions',
]

# SQLObject/SQLBase
from sqlobject import (
    SQLObjectNotFound,
    StringCol,
    )
from storm.store import EmptyResultSet
# Zope imports
from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.helpers import ensure_unicode
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.vocabulary import (
    BatchedCountableIterator,
    NamedSQLObjectHugeVocabulary,
    )
from lp.app.errors import NotFoundError
from lp.soyuz.interfaces.binarypackagename import (
    IBinaryPackageName,
    IBinaryPackageNameSet,
    )
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease


class BinaryPackageName(SQLBase):

    implements(IBinaryPackageName)
    _table = 'BinaryPackageName'
    name = StringCol(dbName='name', notNull=True, unique=True,
                     alternateID=True)

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<BinaryPackageName at %X name=%r>" % (id(self), self.name)


class BinaryPackageNameSet:
    implements(IBinaryPackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        try:
            return BinaryPackageName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def getAll(self):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        return BinaryPackageName.select()

    def findByName(self, name):
        """Find binarypackagenames by its name or part of it."""
        return IStore(BinaryPackageName).find(
            BinaryPackageName,
            BinaryPackageName.name.contains_string(ensure_unicode(name)))

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
        # Here we're returning `BinaryPackageName`s where the records
        # for the supplied `BinaryPackageName` IDs are published in the
        # supplied distroseries.  If they're already published then they
        # must not be new.
        if len(name_ids) == 0:
            return EmptyResultSet()

        statuses = (
            PackagePublishingStatus.PUBLISHED,
            PackagePublishingStatus.PENDING,
            )

        return BinaryPackageName.select("""
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchSeries.distroseries = %s AND
            BinaryPackagePublishingHistory.status IN %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackageRelease.binarypackagename = BinaryPackageName.id AND
            BinaryPackageName.id IN %s
            """ % sqlvalues(distroseries, statuses, archive_ids, name_ids),
            distinct=True,
            clauseTables=["BinaryPackagePublishingHistory",
                          "BinaryPackageRelease",
                          "DistroArchSeries"])


class BinaryPackageNameIterator(BatchedCountableIterator):
    """An iterator for BinaryPackageNameVocabulary.

    Builds descriptions based on releases of that binary package name.
    """

    def getTermsWithDescriptions(self, results):
        # Prefill the descriptions dictionary with the latest
        # description uploaded for that package name.
        descriptions = getBinaryPackageDescriptions(results)
        return [SimpleTerm(obj, obj.name,
                    descriptions.get(obj.name, "Not uploaded"))
                for obj in results]


class BinaryPackageNameVocabulary(NamedSQLObjectHugeVocabulary):
    """A vocabulary for searching for binary package names."""
    _table = BinaryPackageName
    _orderBy = 'name'
    displayname = 'Select a Binary Package'
    iterator = BinaryPackageNameIterator


def getBinaryPackageDescriptions(results, use_names=False,
                                 max_title_length=50):
    """Return a dict of descriptions keyed by package name.

    See sourcepackage.py:getSourcePackageDescriptions, which is analogous.
    """
    if len(list(results)) < 1:
        return {}
    if use_names:
        clause = ("BinaryPackageName.name in %s" %
                 sqlvalues([pn.name for pn in results]))
    else:
        clause = ("BinaryPackageName.id in %s" %
                 sqlvalues([bpn.id for bpn in results]))

    descriptions = {}
    releases = BinaryPackageRelease.select(
        """BinaryPackageRelease.binarypackagename =
            BinaryPackageName.id AND
           %s""" % clause,
        clauseTables=["BinaryPackageRelease", "BinaryPackageName"],
        orderBy=["-BinaryPackageRelease.datecreated"])

    for release in releases:
        binarypackagename = release.binarypackagename.name
        if binarypackagename not in descriptions:
            description = release.description.strip().replace("\n", " ")
            if len(description) > max_title_length:
                description = (release.description[:max_title_length]
                              + "...")
            descriptions[binarypackagename] = description
    return descriptions
