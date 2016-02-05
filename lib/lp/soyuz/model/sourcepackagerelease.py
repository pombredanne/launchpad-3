# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'SourcePackageRelease',
    ]


import datetime
import json
import operator
import re
from StringIO import StringIO

import apt_pkg
from debian.changelog import (
    Changelog,
    ChangelogCreateError,
    ChangelogParseError,
    )
import pytz
from sqlobject import (
    ForeignKey,
    SQLMultipleJoin,
    StringCol,
    )
from storm.expr import Join
from storm.locals import (
    Desc,
    Int,
    Reference,
    )
from storm.store import Store
from zope.component import getUtility
from zope.interface import implementer

from lp.app.errors import NotFoundError
from lp.archiveuploader.utils import determine_source_file_type
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.person import validate_public_person
from lp.registry.interfaces.sourcepackage import (
    SourcePackageType,
    SourcePackageUrgency,
    )
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.sqlbase import (
    cursor,
    SQLBase,
    sqlvalues,
    )
from lp.services.librarian.model import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.soyuz.interfaces.archive import MAIN_ARCHIVE_PURPOSES
from lp.soyuz.interfaces.packagediff import PackageDiffAlreadyRequested
from lp.soyuz.interfaces.packagediffjob import IPackageDiffJobSource
from lp.soyuz.interfaces.queue import QueueInconsistentStateError
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.files import SourcePackageReleaseFile
from lp.soyuz.model.packagediff import PackageDiff
from lp.soyuz.model.queue import (
    PackageUpload,
    PackageUploadSource,
    )


@implementer(ISourcePackageRelease)
class SourcePackageRelease(SQLBase):
    _table = 'SourcePackageRelease'

    section = ForeignKey(foreignKey='Section', dbName='section')
    creator = ForeignKey(
        dbName='creator', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    component = ForeignKey(foreignKey='Component', dbName='component')
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=True)
    maintainer = ForeignKey(
        dbName='maintainer', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    dscsigningkey = ForeignKey(foreignKey='GPGKey', dbName='dscsigningkey')
    urgency = EnumCol(dbName='urgency', schema=SourcePackageUrgency,
        default=SourcePackageUrgency.LOW, notNull=True)
    dateuploaded = UtcDateTimeCol(dbName='dateuploaded', notNull=True,
        default=UTC_NOW)
    dsc = StringCol(dbName='dsc')
    version = StringCol(dbName='version', notNull=True)
    changelog = ForeignKey(foreignKey='LibraryFileAlias', dbName='changelog')
    changelog_entry = StringCol(dbName='changelog_entry')
    builddepends = StringCol(dbName='builddepends')
    builddependsindep = StringCol(dbName='builddependsindep')
    build_conflicts = StringCol(dbName='build_conflicts')
    build_conflicts_indep = StringCol(dbName='build_conflicts_indep')
    architecturehintlist = StringCol(dbName='architecturehintlist')
    homepage = StringCol(dbName='homepage')
    format = EnumCol(dbName='format', schema=SourcePackageType,
        default=SourcePackageType.DPKG, notNull=True)
    upload_distroseries = ForeignKey(foreignKey='DistroSeries',
        dbName='upload_distroseries')
    upload_archive = ForeignKey(
        foreignKey='Archive', dbName='upload_archive', notNull=True)

    source_package_recipe_build_id = Int(name='sourcepackage_recipe_build')
    source_package_recipe_build = Reference(
        source_package_recipe_build_id, 'SourcePackageRecipeBuild.id')

    # XXX cprov 2006-09-26: Those fields are set as notNull and required in
    # ISourcePackageRelease, however they can't be not NULL in DB since old
    # records doesn't satisfy this condition. We will sort it before using
    # 'NoMoreAptFtparchive' implementation for PRIMARY archive. For PPA
    # (primary target) we don't need to populate old records.
    dsc_maintainer_rfc822 = StringCol(dbName='dsc_maintainer_rfc822')
    dsc_standards_version = StringCol(dbName='dsc_standards_version')
    dsc_format = StringCol(dbName='dsc_format')
    dsc_binaries = StringCol(dbName='dsc_binaries')

    # MultipleJoins
    publishings = SQLMultipleJoin('SourcePackagePublishingHistory',
        joinColumn='sourcepackagerelease', orderBy="-datecreated")

    _user_defined_fields = StringCol(dbName='user_defined_fields')

    def __init__(self, *args, **kwargs):
        if 'user_defined_fields' in kwargs:
            kwargs['_user_defined_fields'] = json.dumps(
                kwargs['user_defined_fields'])
            del kwargs['user_defined_fields']
        # copyright isn't on the Storm class, since we don't want it
        # loaded every time. Set it separately.
        if 'copyright' in kwargs:
            copyright = kwargs.pop('copyright')
        super(SourcePackageRelease, self).__init__(*args, **kwargs)
        self.copyright = copyright

    def __repr__(self):
        """Returns an informative representation of a SourcePackageRelease."""
        return '<{cls} {pkg_name} (id: {id}, version: {version})>'.format(
            cls=self.__class__.__name__, pkg_name=self.name,
            id=self.id, version=self.version)

    @property
    def copyright(self):
        """See `ISourcePackageRelease`."""
        store = Store.of(self)
        store.flush()
        return store.execute(
            "SELECT copyright FROM sourcepackagerelease WHERE id=%s",
            (self.id,)).get_one()[0]

    @copyright.setter
    def copyright(self, content):
        """See `ISourcePackageRelease`."""
        store = Store.of(self)
        store.flush()
        if content is not None:
            content = unicode(content)
        store.execute(
            "UPDATE sourcepackagerelease SET copyright=%s WHERE id=%s",
            (content, self.id))

    @property
    def user_defined_fields(self):
        """See `IBinaryPackageRelease`."""
        if self._user_defined_fields is None:
            return []
        user_defined_fields = json.loads(self._user_defined_fields)
        if user_defined_fields is None:
            return []
        return user_defined_fields

    def getUserDefinedField(self, name):
        for k, v in self.user_defined_fields:
            if k.lower() == name.lower():
                return v

    @cachedproperty
    def package_diffs(self):
        return list(Store.of(self).find(
            PackageDiff, to_source=self).order_by(
                Desc(PackageDiff.date_requested)))

    @property
    def builds(self):
        """See `ISourcePackageRelease`."""
        # Excluding PPA builds may seem like a strange thing to do, but,
        # since Archive.copyPackage can copy packages across archives, a
        # build may well have a different archive to the corresponding
        # sourcepackagerelease.
        return BinaryPackageBuild.select("""
            source_package_release = %s AND
            archive.id = binarypackagebuild.archive AND
            archive.purpose IN %s
            """ % sqlvalues(self.id, MAIN_ARCHIVE_PURPOSES),
            orderBy=['-date_created', 'id'],
            clauseTables=['Archive'])

    @property
    def age(self):
        """See ISourcePackageRelease."""
        now = datetime.datetime.now(pytz.timezone('UTC'))
        return now - self.dateuploaded

    def failed_builds(self):
        return [build for build in self._cached_builds
                if build.buildstate == BuildStatus.FAILEDTOBUILD]

    @property
    def needs_building(self):
        for build in self._cached_builds:
            if build.status in [BuildStatus.NEEDSBUILD,
                                    BuildStatus.MANUALDEPWAIT,
                                    BuildStatus.CHROOTWAIT]:
                return True
        return False

    @cachedproperty
    def _cached_builds(self):
        # The reason we have this as a cachedproperty is that all the
        # *build* methods here need access to it; better not to
        # recalculate it multiple times.
        return list(self.builds)

    @property
    def name(self):
        return self.sourcepackagename.name

    @property
    def title(self):
        return '%s - %s' % (self.sourcepackagename.name, self.version)

    @cachedproperty
    def published_archives(self):
        archives = set(
            pub.archive for pub in self.publishings.prejoin(['archive']))
        return sorted(archives, key=operator.attrgetter('id'))

    def addFile(self, file, filetype=None):
        """See ISourcePackageRelease."""
        if filetype is None:
            filetype = determine_source_file_type(file.filename)
        sprf = SourcePackageReleaseFile(
            sourcepackagerelease=self, filetype=filetype, libraryfile=file)
        del get_property_cache(self).files
        return sprf

    @cachedproperty
    def files(self):
        """See `ISourcePackageRelease`."""
        return list(Store.of(self).find(
            SourcePackageReleaseFile, sourcepackagerelease=self).order_by(
                SourcePackageReleaseFile.libraryfileID))

    def getFileByName(self, filename):
        """See `ISourcePackageRelease`."""
        sprf = Store.of(self).find(
            SourcePackageReleaseFile,
            SourcePackageReleaseFile.sourcepackagerelease == self.id,
            LibraryFileAlias.id == SourcePackageReleaseFile.libraryfileID,
            LibraryFileAlias.filename == filename).one()
        if sprf:
            return sprf.libraryfile
        else:
            raise NotFoundError(filename)

    def getPackageSize(self):
        """See ISourcePackageRelease."""
        size_query = """
            SELECT
                SUM(LibraryFileContent.filesize)/1024.0
            FROM
                SourcePackagereLease
                JOIN SourcePackageReleaseFile ON
                    SourcePackageReleaseFile.sourcepackagerelease =
                    SourcePackageRelease.id
                JOIN LibraryFileAlias ON
                    SourcePackageReleaseFile.libraryfile =
                    LibraryFileAlias.id
                JOIN LibraryFileContent ON
                    LibraryFileAlias.content = LibraryFileContent.id
            WHERE
                SourcePackageRelease.id = %s
            """ % sqlvalues(self)

        cur = cursor()
        cur.execute(size_query)
        results = cur.fetchone()

        if len(results) == 1 and results[0] is not None:
            return float(results[0])
        else:
            return 0.0

    def override(self, component=None, section=None, urgency=None):
        """See ISourcePackageRelease."""
        if component is not None:
            self.component = component
            # See if the new component requires a new archive:
            distribution = self.upload_distroseries.distribution
            new_archive = distribution.getArchiveByComponent(component.name)
            if new_archive is not None:
                self.upload_archive = new_archive
            else:
                raise QueueInconsistentStateError(
                    "New component '%s' requires a non-existent archive.")
        if section is not None:
            self.section = section
        if urgency is not None:
            self.urgency = urgency

    @property
    def upload_changesfile(self):
        """See `ISourcePackageRelease`."""
        package_upload = self.package_upload
        # Cope with `SourcePackageRelease`s imported by gina, they do not
        # have a corresponding `PackageUpload` record.
        if package_upload is None:
            return None
        return package_upload.changesfile

    @property
    def package_upload(self):
        """See `ISourcepackageRelease`."""
        store = Store.of(self)
        # The join on 'changesfile' is used for pre-fetching the
        # corresponding library file, so callsites don't have to issue an
        # extra query.
        origin = [
            PackageUploadSource,
            Join(PackageUpload,
                 PackageUploadSource.packageuploadID == PackageUpload.id),
            Join(LibraryFileAlias,
                 LibraryFileAlias.id == PackageUpload.changes_file_id),
            Join(LibraryFileContent,
                 LibraryFileContent.id == LibraryFileAlias.contentID),
            ]
        results = store.using(*origin).find(
            (PackageUpload, LibraryFileAlias, LibraryFileContent),
            PackageUploadSource.sourcepackagerelease == self,
            PackageUpload.archive == self.upload_archive,
            PackageUpload.distroseries == self.upload_distroseries)

        # Return the unique `PackageUpload` record that corresponds to the
        # upload of this `SourcePackageRelease`, load the `LibraryFileAlias`
        # and the `LibraryFileContent` in cache because it's most likely
        # they will be needed.
        return DecoratedResultSet(results, operator.itemgetter(0)).one()

    @property
    def uploader(self):
        """See `ISourcePackageRelease`"""
        if self.source_package_recipe_build is not None:
            return self.source_package_recipe_build.requester
        if self.dscsigningkey is not None:
            return self.dscsigningkey.owner
        return None

    @property
    def change_summary(self):
        """See ISourcePackageRelease"""
        # this regex is copied from apt-listchanges.py courtesy of MDZ
        new_stanza_line = re.compile(
            '^\S+ \((?P<version>.*)\) .*;.*urgency=(?P<urgency>\w+).*')
        logfile = StringIO(self.changelog_entry)
        change = ''
        top_stanza = False
        for line in logfile.readlines():
            match = new_stanza_line.match(line)
            if match:
                if top_stanza:
                    break
                top_stanza = True
            change += line

        return change

    def getDiffTo(self, to_sourcepackagerelease):
        """See ISourcePackageRelease."""
        return PackageDiff.selectOneBy(
            from_source=self, to_source=to_sourcepackagerelease)

    def requestDiffTo(self, requester, to_sourcepackagerelease):
        """See ISourcePackageRelease."""
        candidate = self.getDiffTo(to_sourcepackagerelease)

        if candidate is not None:
            raise PackageDiffAlreadyRequested(
                "%s has already been requested" % candidate.title)

        Store.of(to_sourcepackagerelease).flush()
        del get_property_cache(to_sourcepackagerelease).package_diffs
        packagediff = PackageDiff(
            from_source=self, to_source=to_sourcepackagerelease,
            requester=requester)
        getUtility(IPackageDiffJobSource).create(packagediff)
        return packagediff

    def aggregate_changelog(self, since_version):
        """See `ISourcePackagePublishingHistory`."""
        if self.changelog is None:
            return None

        apt_pkg.init_system()
        chunks = []
        changelog = self.changelog
        # The python-debian API for parsing changelogs is pretty awful. The
        # only useful way of extracting info is to use the iterator on
        # Changelog and then compare versions.
        try:
            changelog_text = changelog.read().decode("UTF-8", "replace")
            for block in Changelog(changelog_text):
                version = block._raw_version
                if (since_version and
                    apt_pkg.version_compare(version, since_version) <= 0):
                    break
                # Poking in private attributes is not nice but again the
                # API is terrible.  We want to ensure that the name/date
                # line is omitted from these composite changelogs.
                block._no_trailer = True
                try:
                    # python-debian adds an extra blank line to the chunks
                    # so we'll have to sort this out.
                    chunks.append(str(block).rstrip())
                except ChangelogCreateError:
                    continue
                if not since_version:
                    # If a particular version was not requested we just
                    # return the most recent changelog entry.
                    break
        except ChangelogParseError:
            return None

        output = "\n\n".join(chunks)
        return output.decode("utf-8", "replace")
