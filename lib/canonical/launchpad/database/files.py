# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'BinaryPackageFile',
    'BinaryPackageFileSet',
    'SourcePackageReleaseFile',
    ]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    BinaryPackageFileType, SourcePackageFileType)
from lp.soyuz.interfaces.files import (
    IBinaryPackageFile, IBinaryPackageFileSet, ISourcePackageReleaseFile,
    ISourcePackageReleaseFileSet)


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
            Build.id = PackageUploadBuild.build AND
            BinaryPackageRelease.build = Build.id AND
            BinaryPackageFile.binarypackagerelease = BinaryPackageRelease.id
            """ % sqlvalues(package_upload_ids),
            clauseTables=["PackageUpload", "PackageUploadBuild", "Build",
                          "BinaryPackageRelease"],
            prejoins=["binarypackagerelease", "binarypackagerelease.build",
                      "libraryfile", "libraryfile.content",
                      "binarypackagerelease.binarypackagename"])


class SourcePackageReleaseFile(SQLBase):
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

