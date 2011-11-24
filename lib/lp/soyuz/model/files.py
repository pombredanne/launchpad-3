# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'BinaryPackageFile',
    'BinaryPackageFileSet',
    'SourceFileMixin',
    'SourcePackageReleaseFile',
    ]

from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.database.librarian import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.services.database.bulk import load_related
from lp.soyuz.enums import BinaryPackageFileType
from lp.soyuz.interfaces.files import (
    IBinaryPackageFile,
    IBinaryPackageFileSet,
    ISourcePackageReleaseFile,
    ISourcePackageReleaseFileSet,
    )


class BinaryPackageFile(SQLBase):
    """See IBinaryPackageFile """
    implements(IBinaryPackageFile)
    _table = 'BinaryPackageFile'

    binarypackagerelease = ForeignKey(dbName='binarypackagerelease',
                                      foreignKey='BinaryPackageRelease',
                                      notNull=True)
    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFileAlias', notNull=True)
    filetype = EnumCol(dbName='filetype',
                       schema=BinaryPackageFileType)


class BinaryPackageFileSet:
    """See `IBinaryPackageFileSet`."""
    implements(IBinaryPackageFileSet)

    def getByPackageUploadIDs(self, package_upload_ids):
        """See `IBinaryPackageFileSet`."""
        if package_upload_ids is None or len(package_upload_ids) == 0:
            return []
        return BinaryPackageFile.select("""
            PackageUploadBuild.packageupload = PackageUpload.id AND
            PackageUpload.id IN %s AND
            BinaryPackageBuild.id = PackageUploadBuild.build AND
            BinaryPackageRelease.build = BinaryPackageBuild.id AND
            BinaryPackageFile.binarypackagerelease = BinaryPackageRelease.id
            """ % sqlvalues(package_upload_ids),
            clauseTables=["PackageUpload", "PackageUploadBuild",
                          "BinaryPackageBuild", "BinaryPackageRelease"],
            prejoins=["binarypackagerelease", "binarypackagerelease.build",
                      "binarypackagerelease.binarypackagename"])

    def loadLibraryFiles(self, binary_files):
        """See `IBinaryPackageFileSet`."""
        lfas = load_related(LibraryFileAlias, binary_files, ['libraryfileID'])
        load_related(LibraryFileContent, lfas, ['contentID'])
        return lfas


class SourceFileMixin:
    """Mix-in class for common functionality between source file classes."""

    @property
    def is_orig(self):
        return self.filetype in (
            SourcePackageFileType.ORIG_TARBALL,
            SourcePackageFileType.COMPONENT_ORIG_TARBALL
            )


class SourcePackageReleaseFile(SourceFileMixin, SQLBase):
    """See ISourcePackageFile"""

    implements(ISourcePackageReleaseFile)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    libraryfile = ForeignKey(foreignKey='LibraryFileAlias',
                             dbName='libraryfile')
    filetype = EnumCol(schema=SourcePackageFileType)


class SourcePackageReleaseFileSet:
    """See `ISourcePackageReleaseFileSet`."""
    implements(ISourcePackageReleaseFileSet)

    def getByPackageUploadIDs(self, package_upload_ids):
        """See `ISourcePackageReleaseFileSet`."""
        if package_upload_ids is None or len(package_upload_ids) == 0:
            return []
        return SourcePackageReleaseFile.select("""
            PackageUploadSource.packageupload = PackageUpload.id AND
            PackageUpload.id IN %s AND
            SourcePackageReleaseFile.sourcepackagerelease =
                PackageUploadSource.sourcepackagerelease
            """ % sqlvalues(package_upload_ids),
            clauseTables=["PackageUpload", "PackageUploadSource"],
            prejoins=["libraryfile", "libraryfile.content",
                      "sourcepackagerelease",
                      "sourcepackagerelease.sourcepackagename"])
