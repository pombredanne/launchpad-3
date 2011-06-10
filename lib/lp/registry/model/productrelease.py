# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'ProductRelease',
    'ProductReleaseFile',
    'ProductReleaseSet',
    'productrelease_to_milestone',
    ]

from StringIO import StringIO

from sqlobject import (
    ForeignKey,
    SQLMultipleJoin,
    StringCol,
    )
from storm.expr import (
    And,
    Desc,
    )
from storm.store import EmptyResultSet
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.app.errors import NotFoundError
from lp.registry.interfaces.person import (
    validate_person,
    validate_public_person,
    )
from lp.registry.interfaces.productrelease import (
    IProductRelease,
    IProductReleaseFile,
    IProductReleaseSet,
    UpstreamFileType,
    )


SEEK_END = 2                    # Python2.4 has no definition for SEEK_END.


class ProductRelease(SQLBase):
    """A release of a product."""
    implements(IProductRelease)
    _table = 'ProductRelease'
    _defaultOrder = ['-datereleased']

    datereleased = UtcDateTimeCol(notNull=True)
    release_notes = StringCol(notNull=False, default=None)
    changelog = StringCol(notNull=False, default=None)
    datecreated = UtcDateTimeCol(
        dbName='datecreated', notNull=True, default=UTC_NOW)
    owner = ForeignKey(
        dbName="owner", foreignKey="Person",
        storm_validator=validate_person,
        notNull=True)
    milestone = ForeignKey(dbName='milestone', foreignKey='Milestone')

    files = SQLMultipleJoin(
        'ProductReleaseFile', joinColumn='productrelease',
        orderBy='-date_uploaded', prejoins=['productrelease'])

    # properties
    @property
    def codename(self):
        """Backwards compatible codename attribute.

        This attribute was moved to the Milestone."""
        # XXX EdwinGrubbs 2009-02-02 bug=324394: Remove obsolete attributes.
        return self.milestone.code_name

    @property
    def version(self):
        """Backwards compatible version attribute.

        This attribute was replaced by the Milestone.name."""
        # XXX EdwinGrubbs 2009-02-02 bug=324394: Remove obsolete attributes.
        return self.milestone.name

    @property
    def summary(self):
        """Backwards compatible summary attribute.

        This attribute was replaced by the Milestone.summary."""
        # XXX EdwinGrubbs 2009-02-02 bug=324394: Remove obsolete attributes.
        return self.milestone.summary

    @property
    def productseries(self):
        """Backwards compatible summary attribute.

        This attribute was replaced by the Milestone.productseries."""
        # XXX EdwinGrubbs 2009-02-02 bug=324394: Remove obsolete attributes.
        return self.milestone.productseries

    @property
    def product(self):
        """Backwards compatible summary attribute.

        This attribute was replaced by the Milestone.productseries.product."""
        # XXX EdwinGrubbs 2009-02-02 bug=324394: Remove obsolete attributes.
        return self.productseries.product

    @property
    def displayname(self):
        """See `IProductRelease`."""
        return self.milestone.displayname

    @property
    def title(self):
        """See `IProductRelease`."""
        return self.milestone.title

    @staticmethod
    def normalizeFilename(filename):
        # Replace slashes in the filename with less problematic dashes.
        return filename.replace('/', '-')

    def destroySelf(self):
        """See `IProductRelease`."""
        assert self.files.count() == 0, (
            "You can't delete a product release which has files associated "
            "with it.")
        SQLBase.destroySelf(self)

    def _getFileObjectAndSize(self, file_or_data):
        """Return an object and length for file_or_data.

        :param file_or_data: A string or a file object or StringIO object.
        :return: file object or StringIO object and size.
        """
        if isinstance(file_or_data, basestring):
            file_size = len(file_or_data)
            file_obj = StringIO(file_or_data)
        else:
            assert isinstance(file_or_data, (file, StringIO)), (
                "file_or_data is not an expected type")
            file_obj = file_or_data
            start = file_obj.tell()
            file_obj.seek(0, SEEK_END)
            file_size = file_obj.tell()
            file_obj.seek(start)
        return file_obj, file_size

    def addReleaseFile(self, filename, file_content, content_type,
                       uploader, signature_filename=None,
                       signature_content=None,
                       file_type=UpstreamFileType.CODETARBALL,
                       description=None):
        """See `IProductRelease`."""
        # Create the alias for the file.
        filename = self.normalizeFilename(filename)
        file_obj, file_size = self._getFileObjectAndSize(file_content)

        alias = getUtility(ILibraryFileAliasSet).create(
            name=filename,
            size=file_size,
            file=file_obj,
            contentType=content_type)
        if signature_filename is not None and signature_content is not None:
            signature_obj, signature_size = self._getFileObjectAndSize(
                signature_content)
            signature_filename = self.normalizeFilename(
                signature_filename)
            signature_alias = getUtility(ILibraryFileAliasSet).create(
                name=signature_filename,
                size=signature_size,
                file=signature_obj,
                contentType='application/pgp-signature')
        else:
            signature_alias = None
        return ProductReleaseFile(productrelease=self,
                                  libraryfile=alias,
                                  signature=signature_alias,
                                  filetype=file_type,
                                  description=description,
                                  uploader=uploader)

    def getFileAliasByName(self, name):
        """See `IProductRelease`."""
        for file_ in self.files:
            if file_.libraryfile.filename == name:
                return file_.libraryfile
            elif file_.signature and file_.signature.filename == name:
                return file_.signature
        raise NotFoundError(name)

    def getProductReleaseFileByName(self, name):
        """See `IProductRelease`."""
        for file_ in self.files:
            if file_.libraryfile.filename == name:
                return file_
        raise NotFoundError(name)


class ProductReleaseFile(SQLBase):
    """A file of a product release."""
    implements(IProductReleaseFile)

    _table = 'ProductReleaseFile'

    productrelease = ForeignKey(dbName='productrelease',
                                foreignKey='ProductRelease', notNull=True)

    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFileAlias', notNull=True)

    signature = ForeignKey(dbName='signature',
                           foreignKey='LibraryFileAlias')

    filetype = EnumCol(dbName='filetype', enum=UpstreamFileType,
                       notNull=True, default=UpstreamFileType.CODETARBALL)

    description = StringCol(notNull=False, default=None)

    uploader = ForeignKey(
        dbName="uploader", foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)

    date_uploaded = UtcDateTimeCol(notNull=True, default=UTC_NOW)


class ProductReleaseSet(object):
    """See `IProductReleaseSet`."""
    implements(IProductReleaseSet)

    def getBySeriesAndVersion(self, productseries, version, default=None):
        """See `IProductReleaseSet`."""
        # Local import of Milestone to avoid circular imports.
        from lp.registry.model.milestone import Milestone
        store = IStore(productseries)
        # The Milestone is cached too because most uses of a ProductRelease
        # need it.
        result = store.find(
            (ProductRelease, Milestone),
            Milestone.productseries == productseries,
            ProductRelease.milestone == Milestone.id,
            Milestone.name == version)
        found = result.one()
        if found is None:
            return None
        product_release, milestone = found
        return product_release

    def getReleasesForSeries(self, series):
        """See `IProductReleaseSet`."""
        # Local import of Milestone to avoid import loop.
        from lp.registry.model.milestone import Milestone
        if len(list(series)) == 0:
            return EmptyResultSet()
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        series_ids = [s.id for s in series]
        result = store.find(
            ProductRelease,
            And(ProductRelease.milestone == Milestone.id),
                Milestone.productseriesID.is_in(series_ids))
        return result.order_by(Desc(ProductRelease.datereleased))

    def getFilesForReleases(self, releases):
        """See `IProductReleaseSet`."""
        releases = list(releases)
        if len(releases) == 0:
            return EmptyResultSet()
        return ProductReleaseFile.select(
            """ProductReleaseFile.productrelease IN %s""" % (
            sqlvalues([release.id for release in releases])),
            orderBy='-date_uploaded',
            prejoins=['libraryfile', 'libraryfile.content', 'productrelease'])


def productrelease_to_milestone(productrelease):
    """Adapt an `IProductRelease` to an `IMilestone`."""
    return productrelease.milestone
