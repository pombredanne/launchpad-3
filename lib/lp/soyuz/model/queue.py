# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'PackageUploadQueue',
    'PackageUpload',
    'PackageUploadBuild',
    'PackageUploadSource',
    'PackageUploadCustom',
    'PackageUploadSet',
    ]

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import shutil
import StringIO
import tempfile

from sqlobject import (
    ForeignKey,
    SQLMultipleJoin,
    SQLObjectNotFound,
    )
from storm.locals import (
    Desc,
    Join,
    )
from storm.store import Store
from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.encoding import (
    ascii_smash,
    guess as guess_encoding,
    )
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.mail import (
    format_address,
    sendmail,
    signed_message_from_string,
    )
from canonical.launchpad.webapp import canonical_url
from canonical.librarian.interfaces import DownloadFailed
from canonical.librarian.utils import copy_and_close
from lp.app.errors import NotFoundError
# XXX 2009-05-10 julian
# This should not import from archivepublisher, but to avoid
# that it needs a bit of redesigning here around the publication stuff.
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.customupload import CustomUploadError
from lp.archivepublisher.utils import get_ppa_reference
from lp.archiveuploader.changesfile import ChangesFile
from lp.archiveuploader.tagfiles import parse_tagfile_lines
from lp.archiveuploader.utils import safe_fix_maintainer
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.services.propertycache import cachedproperty
from lp.soyuz.enums import (
    BinaryPackageFormat,
    PackageUploadCustomFormat,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import MAIN_ARCHIVE_PURPOSES
from lp.soyuz.interfaces.publishing import (
    IPublishingSet,
    ISourcePackagePublishingHistory,
    )
from lp.soyuz.interfaces.queue import (
    IPackageUpload,
    IPackageUploadBuild,
    IPackageUploadCustom,
    IPackageUploadQueue,
    IPackageUploadSet,
    IPackageUploadSource,
    NonBuildableSourceUploadError,
    QueueBuildAcceptError,
    QueueInconsistentStateError,
    QueueSourceAcceptError,
    QueueStateWriteProtectedError,
    )
from lp.soyuz.pas import BuildDaemonPackagesArchSpecific
from lp.soyuz.scripts.packagecopier import update_files_privacy
from lp.soyuz.scripts.processaccepted import close_bugs_for_queue_item

# There are imports below in PackageUploadCustom for various bits
# of the archivepublisher which cause circular import errors if they
# are placed here.

def debug(logger, msg):
    """Shorthand debug notation for publish() methods."""
    if logger is not None:
        logger.debug(msg)


class PassthroughStatusValue:
    """A wrapper to allow setting PackageUpload.status."""

    def __init__(self, value):
        self.value = value


def validate_status(self, attr, value):
    # Is the status wrapped in the special passthrough class?
    if isinstance(value, PassthroughStatusValue):
        return value.value

    if self._SO_creating:
        return value
    else:
        raise QueueStateWriteProtectedError(
            'Directly write on queue status is forbidden use the '
            'provided methods to set it.')


def sanitize_string(s):
    """Make sure string does not trigger 'ascii' codec errors.

    Convert string to unicode if needed so that characters outside
    the (7-bit) ASCII range do not cause errors like these:

        'ascii' codec can't decode byte 0xc4 in position 21: ordinal
        not in range(128)
    """
    if isinstance(s, unicode):
        return s
    else:
        return guess_encoding(s)


class PackageUploadQueue:

    implements(IPackageUploadQueue)

    def __init__(self, distroseries, status):
        self.distroseries = distroseries
        self.status = status


class LanguagePackEncountered(Exception):
    """Thrown when not wanting to email notifications for language packs."""


class PackageUpload(SQLBase):
    """A Queue item for the archive uploader."""

    implements(IPackageUpload)

    _defaultOrder = ['id']

    status = EnumCol(dbName='status', unique=False, notNull=True,
                     default=PackageUploadStatus.NEW,
                     schema=PackageUploadStatus,
                     storm_validator=validate_status)

    date_created = UtcDateTimeCol(notNull=False, default=UTC_NOW)

    distroseries = ForeignKey(dbName="distroseries",
                               foreignKey='DistroSeries')

    pocket = EnumCol(dbName='pocket', unique=False, notNull=True,
                     schema=PackagePublishingPocket)

    changesfile = ForeignKey(
        dbName='changesfile', foreignKey="LibraryFileAlias", notNull=False)

    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)

    signing_key = ForeignKey(foreignKey='GPGKey', dbName='signing_key',
                             notNull=False)

    # XXX julian 2007-05-06:
    # Sources should not be SQLMultipleJoin, there is only ever one
    # of each at most.

    # Join this table to the PackageUploadBuild and the
    # PackageUploadSource objects which are related.
    sources = SQLMultipleJoin('PackageUploadSource',
                              joinColumn='packageupload')
    # Does not include source builds.
    builds = SQLMultipleJoin('PackageUploadBuild',
                             joinColumn='packageupload')

    def getSourceBuild(self):
        #avoid circular import
        from lp.code.model.sourcepackagerecipebuild import (
            SourcePackageRecipeBuild)
        from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
        return Store.of(self).find(
            SourcePackageRecipeBuild,
            SourcePackageRecipeBuild.id ==
                SourcePackageRelease.source_package_recipe_build_id,
            SourcePackageRelease.id ==
            PackageUploadSource.sourcepackagereleaseID,
            PackageUploadSource.packageupload == self.id).one()

    # Also the custom files associated with the build.
    customfiles = SQLMultipleJoin('PackageUploadCustom',
                                  joinColumn='packageupload')

    @property
    def custom_file_urls(self):
        """See `IPackageUpload`."""
        return tuple(
            file.libraryfilealias.getURL() for file in self.customfiles)

    def setNew(self):
        """See `IPackageUpload`."""
        if self.status == PackageUploadStatus.NEW:
            raise QueueInconsistentStateError(
                'Queue item already new')
        self.status = PassthroughStatusValue(PackageUploadStatus.NEW)

    def setUnapproved(self):
        """See `IPackageUpload`."""
        if self.status == PackageUploadStatus.UNAPPROVED:
            raise QueueInconsistentStateError(
                'Queue item already unapproved')
        self.status = PassthroughStatusValue(PackageUploadStatus.UNAPPROVED)

    def setAccepted(self):
        """See `IPackageUpload`."""
        # Explode if something wrong like warty/RELEASE pass through
        # NascentUpload/UploadPolicies checks for 'ubuntu' main distro.
        if not self.archive.allowUpdatesToReleasePocket():
            assert self.distroseries.canUploadToPocket(self.pocket), (
                "Not permitted acceptance in the %s pocket in a "
                "series in the '%s' state." % (
                self.pocket.name, self.distroseries.status.name))

        if self.status == PackageUploadStatus.ACCEPTED:
            raise QueueInconsistentStateError(
                'Queue item already accepted')

        for source in self.sources:
            source.verifyBeforeAccept()
            # if something goes wrong we will raise an exception
            # (QueueSourceAcceptError) before setting any value.
            # Mask the error with state-machine default exception
            try:
                source.checkComponentAndSection()
            except QueueSourceAcceptError, info:
                raise QueueInconsistentStateError(info)

        self._checkForBinariesinDestinationArchive(
            [queue_build.build for queue_build in self.builds])
        for queue_build in self.builds:
            try:
                queue_build.checkComponentAndSection()
            except QueueBuildAcceptError, info:
                raise QueueInconsistentStateError(info)

        # if the previous checks applied and pass we do set the value
        self.status = PassthroughStatusValue(PackageUploadStatus.ACCEPTED)

    def _checkForBinariesinDestinationArchive(self, builds):
        """
        Check for existing binaries (in destination archive) for all binary
        uploads to be accepted.

        Before accepting binary uploads we check whether any of the binaries
        already exists in the destination archive and raise an exception
        (QueueInconsistentStateError) if this is the case.

        The only way to find pre-existing binaries is to match on binary
        package file names.
        """
        if len(builds) == 0:
            return

        # Collects the binary file names for all builds.
        inner_query = """
            SELECT DISTINCT lfa.filename
            FROM
                binarypackagefile bpf, binarypackagerelease bpr,
                libraryfilealias lfa
            WHERE
                bpr.build IN %s
                AND bpf.binarypackagerelease = bpr.id
                AND bpf.libraryfile = lfa.id
        """ % sqlvalues([build.id for build in builds])

        # Check whether any of the binary file names have already been
        # published in the destination archive.
        query = """
            SELECT DISTINCT lfa.filename
            FROM
                binarypackagefile bpf, binarypackagepublishinghistory bpph,
                distroarchseries das, distroseries ds, libraryfilealias lfa
            WHERE
                bpph.archive = %s
                AND bpph.distroarchseries = das.id
                AND bpph.dateremoved IS NULL
                AND das.distroseries = ds.id
                AND ds.distribution = %s
                AND bpph.binarypackagerelease = bpf.binarypackagerelease
                AND bpf.libraryfile = lfa.id
                AND lfa.filename IN (%%s)
        """ % sqlvalues(self.archive, self.distroseries.distribution)
        # Inject the inner query.
        query %= inner_query

        store = Store.of(self)
        result_set = store.execute(query)
        known_filenames = [row[0] for row in result_set.get_all()]

        # Do any of the files to be uploaded already exist in the destination
        # archive?
        if len(known_filenames) > 0:
            filename_list = "\n\t%s".join(
                [filename for filename in known_filenames])
            raise QueueInconsistentStateError(
                'The following files are already published in %s:\n%s' % (
                    self.archive.displayname, filename_list))

    def setDone(self):
        """See `IPackageUpload`."""
        if self.status == PackageUploadStatus.DONE:
            raise QueueInconsistentStateError(
                'Queue item already done')
        self.status = PassthroughStatusValue(PackageUploadStatus.DONE)

    def setRejected(self):
        """See `IPackageUpload`."""
        if self.status == PackageUploadStatus.REJECTED:
            raise QueueInconsistentStateError(
                'Queue item already rejected')
        self.status = PassthroughStatusValue(PackageUploadStatus.REJECTED)

    def _closeBugs(self, changesfile_path, logger=None):
        """Close bugs for a just-accepted source.

        :param changesfile_path: path to the context changesfile.
        :param logger: optional context Logger object (used on DEBUG level);

        It does not close bugs for PPA sources.
        """
        if self.isPPA():
            debug(logger, "Not closing bugs for PPA source.")
            return

        debug(logger, "Closing bugs.")
        changesfile_object = open(changesfile_path, 'r')
        close_bugs_for_queue_item(
            self, changesfile_object=changesfile_object)
        changesfile_object.close()

    def _validateBuildsForSource(self, sourcepackagerelease, builds):
        """Check if the sourcepackagerelease generates at least one build.

        :raise NonBuildableSourceUploadError: when the uploaded source
            doesn't result in any builds in its targeted distroseries.
        """
        if len(builds) == 0 and self.isPPA():
            raise NonBuildableSourceUploadError(
                "Cannot build any of the architectures requested: %s" %
                sourcepackagerelease.architecturehintlist)

    def _giveKarma(self):
        """Assign karma as appropriate for an accepted upload."""
        # Give some karma to the uploader for source uploads only.
        if not bool(self.sources):
            return

        changed_by = self.sources[0].sourcepackagerelease.creator
        if self.signing_key is not None:
            uploader = self.signing_key.owner
        else:
            uploader = None

        if self.archive.is_ppa:
            main_karma_action = 'ppauploadaccepted'
        else:
            main_karma_action = 'distributionuploadaccepted'

        distribution = self.distroseries.distribution
        sourcepackagename = self.sources[
            0].sourcepackagerelease.sourcepackagename

        # The package creator always gets his karma.
        changed_by.assignKarma(
            main_karma_action, distribution=distribution,
            sourcepackagename=sourcepackagename)

        if self.archive.is_ppa:
            return

        # If a sponsor was involved, give him some too.
        if uploader is not None and changed_by != uploader:
            uploader.assignKarma(
                'sponsoruploadaccepted', distribution=distribution,
                sourcepackagename=sourcepackagename)

    def acceptFromUploader(self, changesfile_path, logger=None):
        """See `IPackageUpload`."""
        assert not self.is_delayed_copy, 'Cannot process delayed copies.'

        debug(logger, "Setting it to ACCEPTED")
        self.setAccepted()

        # If it is a pure-source upload we can further process it
        # in order to have a pending publishing record in place.
        # This change is based on discussions for bug #77853 and aims
        # to fix a deficiency on published file lookup system.
        if not self._isSingleSourceUpload():
            return

        debug(logger, "Creating PENDING publishing record.")
        [pub_source] = self.realiseUpload()
        pas_verify = BuildDaemonPackagesArchSpecific(
            config.builddmaster.root, self.distroseries)
        builds = pub_source.createMissingBuilds(
            pas_verify=pas_verify, logger=logger)
        self._validateBuildsForSource(pub_source.sourcepackagerelease, builds)
        self._closeBugs(changesfile_path, logger)
        self._giveKarma()

    def acceptFromQueue(self, announce_list, logger=None, dry_run=False):
        """See `IPackageUpload`."""
        assert not self.is_delayed_copy, 'Cannot process delayed copies.'

        self.setAccepted()
        changes_file_object = StringIO.StringIO(self.changesfile.read())
        # We explicitly allow unsigned uploads here since the .changes file
        # is pulled from the librarian which are stripped of their
        # signature just before being stored.
        self.notify(
            announce_list=announce_list, logger=logger, dry_run=dry_run,
            changes_file_object=changes_file_object, allow_unsigned=True)
        self.syncUpdate()

        # If this is a single source upload we can create the
        # publishing records now so that the user doesn't have to
        # wait for a publisher cycle (which calls process-accepted
        # to do this).
        if self._isSingleSourceUpload():
            [pub_source] = self.realiseUpload()
            builds = pub_source.createMissingBuilds()
            self._validateBuildsForSource(
                pub_source.sourcepackagerelease, builds)

        # When accepting packages, we must also check the changes file
        # for bugs to close automatically.
        close_bugs_for_queue_item(self)

        # Give some karma!
        self._giveKarma()

    def acceptFromCopy(self):
        """See `IPackageUpload`."""
        assert self.is_delayed_copy, 'Can only process delayed-copies.'
        assert self.sources.count() == 1, (
            'Source is mandatory for delayed copies.')
        self.setAccepted()

    def rejectFromQueue(self, logger=None, dry_run=False):
        """See `IPackageUpload`."""
        self.setRejected()
        changes_file_object = StringIO.StringIO(self.changesfile.read())
        # We allow unsigned uploads since they come from the librarian,
        # which are now stored unsigned.
        self.notify(
            logger=logger, dry_run=dry_run,
            changes_file_object=changes_file_object, allow_unsigned=True)
        self.syncUpdate()

    @property
    def is_delayed_copy(self):
        """See `IPackageUpload`."""
        return self.changesfile is None

    def _isSingleSourceUpload(self):
        """Return True if this upload contains only a single source."""
        return ((self.sources.count() == 1) and
                (not bool(self.builds)) and
                (not bool(self.customfiles)))

    # XXX cprov 2006-03-14: Following properties should be redesigned to
    # reduce the duplicated code.
    @cachedproperty
    def contains_source(self):
        """See `IPackageUpload`."""
        return self.sources

    @cachedproperty
    def contains_build(self):
        """See `IPackageUpload`."""
        return self.builds

    @cachedproperty
    def from_build(self):
        return bool(self.builds) or self.getSourceBuild()

    def isAutoSyncUpload(self, changed_by_email):
        """See `IPackageUpload`."""
        katie = getUtility(ILaunchpadCelebrities).katie
        changed_by = self._emailToPerson(changed_by_email)
        return (not self.signing_key
                and self.contains_source and not self.contains_build
                and changed_by == katie
                and self.pocket != PackagePublishingPocket.SECURITY)

    @cachedproperty
    def _customFormats(self):
        """Return the custom upload formats contained in this upload."""
        return [custom.customformat for custom in self.customfiles]

    @cachedproperty
    def contains_installer(self):
        """See `IPackageUpload`."""
        return (PackageUploadCustomFormat.DEBIAN_INSTALLER
                in self._customFormats)

    @cachedproperty
    def contains_translation(self):
        """See `IPackageUpload`."""
        return (PackageUploadCustomFormat.ROSETTA_TRANSLATIONS
                in self._customFormats)

    @cachedproperty
    def contains_upgrader(self):
        """See `IPackageUpload`."""
        return (PackageUploadCustomFormat.DIST_UPGRADER
                in self._customFormats)

    @cachedproperty
    def contains_ddtp(self):
        """See `IPackageUpload`."""
        return (PackageUploadCustomFormat.DDTP_TARBALL
                in self._customFormats)

    @cachedproperty
    def displayname(self):
        """See `IPackageUpload`"""
        names = []
        for queue_source in self.sources:
            names.append(queue_source.sourcepackagerelease.name)
        for queue_build in self.builds:
            names.append(queue_build.build.source_package_release.name)
        for queue_custom in self.customfiles:
            names.append(queue_custom.libraryfilealias.filename)
        # Make sure the list items have a whitespace separator so
        # that they can be wrapped in table cells in the UI.
        ret = ", ".join(names)
        if self.is_delayed_copy:
            ret += " (delayed)"
        return ret

    @cachedproperty
    def displayarchs(self):
        """See `IPackageUpload`"""
        archs = []
        for queue_source in self.sources:
            archs.append('source')
        for queue_build in self.builds:
            archs.append(queue_build.build.distro_arch_series.architecturetag)
        for queue_custom in self.customfiles:
            archs.append(queue_custom.customformat.title)
        return ", ".join(archs)

    @cachedproperty
    def displayversion(self):
        """See `IPackageUpload`"""
        if self.sources:
            return self.sources[0].sourcepackagerelease.version
        if self.builds:
            return self.builds[0].build.source_package_release.version
        if self.customfiles:
            return '-'

    @cachedproperty
    def sourcepackagerelease(self):
        """The source package release related to this queue item.

        This is currently heuristic but may be more easily calculated later.
        """
        if self.sources:
            return self.sources[0].sourcepackagerelease
        elif self.builds:
            return self.builds[0].build.source_package_release
        else:
            return None

    @property
    def my_source_package_release(self):
        """The source package release related to this queue item.

        al-maisan, Wed, 30 Sep 2009 17:58:31 +0200:
        The cached property version above behaves very finicky in
        tests and I've had a *hell* of a time revising these and
        making them pass.

        In any case, Celso's advice was to stay away from it
        and I am hence introducing this non-cached variant for
        usage inside the content class.
        """
        if self.sources is not None and bool(self.sources):
            return self.sources[0].sourcepackagerelease
        elif self.builds is not None and bool(self.builds):
            return self.builds[0].build.source_package_release
        else:
            return None

    def realiseUpload(self, logger=None):
        """See `IPackageUpload`."""
        assert self.status == PackageUploadStatus.ACCEPTED, (
            "Can not publish a non-ACCEPTED queue record (%s)" % self.id)
        # Explode if something wrong like warty/RELEASE pass through
        # NascentUpload/UploadPolicies checks
        if not self.archive.allowUpdatesToReleasePocket():
            assert self.distroseries.canUploadToPocket(self.pocket), (
                "Not permitted to publish to the %s pocket in a "
                "series in the '%s' state." % (
                self.pocket.name, self.distroseries.status.name))

        publishing_records = []
        # In realising an upload we first load all the sources into
        # the publishing tables, then the binaries, then we attempt
        # to publish the custom objects.
        for queue_source in self.sources:
            queue_source.verifyBeforePublish()
            publishing_records.append(queue_source.publish(logger))
        for queue_build in self.builds:
            publishing_records.extend(queue_build.publish(logger))
        for customfile in self.customfiles:
            try:
                customfile.publish(logger)
            except CustomUploadError, e:
                if logger is not None:
                    logger.error("Queue item ignored: %s" % e)
                    return []

        # Adjust component and file privacy of delayed_copies.
        if self.is_delayed_copy:
            for pub_record in publishing_records:
                pub_record.overrideFromAncestry()

                # Grab the .changes file of the original source package while
                # it's available.
                changes_file = None
                if ISourcePackagePublishingHistory.providedBy(pub_record):
                    release = pub_record.sourcepackagerelease
                    changes_file = release.package_upload.changesfile

                for new_file in update_files_privacy(pub_record):
                    debug(logger,
                          "Re-uploaded %s to librarian" % new_file.filename)
                for custom_file in self.customfiles:
                    update_files_privacy(custom_file)
                    debug(logger,
                          "Re-uploaded custom file %s to librarian" %
                          custom_file.libraryfilealias.filename)
                if ISourcePackagePublishingHistory.providedBy(pub_record):
                    pas_verify = BuildDaemonPackagesArchSpecific(
                        config.builddmaster.root, self.distroseries)
                    pub_record.createMissingBuilds(
                        pas_verify=pas_verify, logger=logger)

                if changes_file is not None:
                    debug(
                        logger,
                        "sending email to %s" % self.distroseries.changeslist)
                    changes_file_object = StringIO.StringIO(
                        changes_file.read())
                    self.notify(
                        announce_list=self.distroseries.changeslist,
                        changes_file_object=changes_file_object,
                        allow_unsigned=True, logger=logger)
                    self.syncUpdate()

        self.setDone()

        return publishing_records

    def addSource(self, spr):
        """See `IPackageUpload`."""
        return PackageUploadSource(
            packageupload=self,
            sourcepackagerelease=spr.id)

    def addBuild(self, build):
        """See `IPackageUpload`."""
        return PackageUploadBuild(
            packageupload=self,
            build=build.id)

    def addCustom(self, library_file, custom_type):
        """See `IPackageUpload`."""
        return PackageUploadCustom(
            packageupload=self,
            libraryfilealias=library_file.id,
            customformat=custom_type)

    def isPPA(self):
        """See `IPackageUpload`."""
        return self.archive.is_ppa

    def _stripPgpSignature(self, changes_lines):
        """Strip any PGP signature from the supplied changes lines."""
        text = "".join(changes_lines)
        signed_message = signed_message_from_string(text)
        # For unsigned '.changes' files we'll get a None `signedContent`.
        if signed_message.signedContent is not None:
            return signed_message.signedContent.splitlines(True)
        else:
            return changes_lines

    def _getChangesDict(self, changes_file_object=None, allow_unsigned=None):
        """Return a dictionary with changes file tags in it."""
        changes_lines = None
        if changes_file_object is None:
            changes_file_object = self.changesfile
            changes_lines = self.changesfile.read().splitlines(True)
        else:
            changes_lines = changes_file_object.readlines()

        # Rewind the file so that the next read starts at offset zero. Please
        # note that a LibraryFileAlias does not support seek operations.
        if hasattr(changes_file_object, "seek"):
            changes_file_object.seek(0)

        # When the 'changesfile' content comes from a different
        # `PackageUpload` instance (e.g. when dealing with delayed copies)
        # we need to be able to specify the "allow unsigned" flag explicitly.
        # In that case the presence of the signing key is immaterial.
        if allow_unsigned is None:
            unsigned = not self.signing_key
        else:
            unsigned = allow_unsigned
        changes = parse_tagfile_lines(changes_lines, allow_unsigned=unsigned)

        # Leaving the PGP signature on a package uploaded
        # leaves the possibility of someone hijacking the notification
        # and uploading to any archive as the signer.
        changes_lines = self._stripPgpSignature(changes_lines)

        return changes, changes_lines

    def _buildUploadedFilesList(self):
        """Return a list of tuples of (filename, component, section).

        Component and section are only set where the file is a source upload.
        If an empty list is returned, it means there are no files.
        Raises LanguagePackRejection if a language pack is detected.
        No emails should be sent for language packs.
        """
        files = []
        if self.contains_source:
            [source] = self.sources
            spr = source.sourcepackagerelease
            # Bail out early if this is an upload for the translations
            # section.
            if spr.section.name == 'translations':
                debug(self.logger,
                    "Skipping acceptance and announcement, it is a "
                    "language-package upload.")
                raise LanguagePackEncountered
            for sprfile in spr.files:
                files.append(
                    (sprfile.libraryfile.filename, spr.component.name,
                     spr.section.name))

        # Component and section don't get set for builds and custom, since
        # this information is only used in the summary string for source
        # uploads.
        for build in self.builds:
            for bpr in build.build.binarypackages:
                files.extend([
                    (bpf.libraryfile.filename, '', '') for bpf in bpr.files])

        if self.customfiles:
            files.extend(
                [(file.libraryfilealias.filename, '', '')
                for file in self.customfiles])

        return files

    def _buildSummary(self, files):
        """Build a summary string based on the files present in the upload."""
        summary = []
        for filename, component, section in files:
            if self.status == PackageUploadStatus.NEW:
                summary.append("NEW: %s" % filename)
            else:
                summary.append(" OK: %s" % filename)
                if filename.endswith("dsc"):
                    summary.append("     -> Component: %s Section: %s" % (
                        component, section))
        return summary

    def _handleCommonBodyContent(self, message, changes):
        """Put together pieces of the body common to all emails.

        Sets the date, changed-by, maintainer, signer and origin properties on
        the message as appropriate.

        :message: An object containing the various pieces of the notification
            email.
        :changes: A dictionary with the changes file content.
        """
        # Add the date field.
        message.DATE = 'Date: %s' % changes['Date']

        # Add the debian 'Changed-By:' field.
        changed_by = changes.get('Changed-By')
        if changed_by is not None:
            changed_by = sanitize_string(changed_by)
            message.CHANGEDBY = '\nChanged-By: %s' % changed_by

        # Add maintainer if present and different from changed-by.
        maintainer = changes.get('Maintainer')
        if maintainer is not None:
            maintainer = sanitize_string(maintainer)
            if maintainer != changed_by:
                message.MAINTAINER = '\nMaintainer: %s' % maintainer

        # Add a 'Signed-By:' line if this is a signed upload and the
        # signer/sponsor differs from the changed-by.
        if self.signing_key is not None:
            # This is a signed upload.
            signer = self.signing_key.owner

            signer_name = sanitize_string(signer.displayname)
            signer_email = sanitize_string(signer.preferredemail.email)

            signer_signature = '%s <%s>' % (signer_name, signer_email)

            if changed_by != signer_signature:
                message.SIGNER = '\nSigned-By: %s' % signer_signature

        # Add the debian 'Origin:' field if present.
        if changes.get('Origin') is not None:
            message.ORIGIN = '\nOrigin: %s' % changes['Origin']

        if self.sources or self.builds:
            message.SPR_URL = canonical_url(self.my_source_package_release)

    def _sendRejectionNotification(
        self, recipients, changes_lines, changes, summary_text, dry_run,
        changesfile_content):
        """Send a rejection email."""

        class PPARejectedMessage:
            """PPA rejected message."""
            template = get_email_template('ppa-upload-rejection.txt')
            SUMMARY = sanitize_string(summary_text)
            CHANGESFILE = sanitize_string(
                ChangesFile.formatChangesComment("".join(changes_lines)))
            USERS_ADDRESS = config.launchpad.users_address

        class RejectedMessage:
            """Rejected message."""
            template = get_email_template('upload-rejection.txt')
            SUMMARY = sanitize_string(summary_text)
            CHANGESFILE = sanitize_string(
                ChangesFile.formatChangesComment(changes['Changes']))
            CHANGEDBY = ''
            ORIGIN = ''
            SIGNER = ''
            MAINTAINER = ''
            SPR_URL = ''
            USERS_ADDRESS = config.launchpad.users_address,

        default_recipient = "%s <%s>" % (
            config.uploader.default_recipient_name,
            config.uploader.default_recipient_address)
        if not recipients:
            recipients = [default_recipient]

        debug(self.logger, "Sending rejection email.")
        if self.isPPA():
            message = PPARejectedMessage
            attach_changes = False
        else:
            message = RejectedMessage
            attach_changes = True

        self._handleCommonBodyContent(message, changes)
        if summary_text is None:
            message.SUMMARY = 'Rejected by archive administrator.'

        body = message.template % message.__dict__

        subject = "%s rejected" % self.changesfile.filename
        if self.isPPA():
            subject = "[PPA %s] %s" % (
                get_ppa_reference(self.archive), subject)

        self._sendMail(
            recipients, subject, body, dry_run,
            changesfile_content=changesfile_content,
            attach_changes=attach_changes)

    def _sendSuccessNotification(
        self, recipients, announce_list, changes_lines, changes,
        summarystring, dry_run, changesfile_content):
        """Send a success email."""

        def do_sendmail(message, recipients=recipients, from_addr=None,
                        bcc=None):
            """Perform substitutions on a template and send the email."""
            self._handleCommonBodyContent(message, changes)
            body = message.template % message.__dict__

            # Weed out duplicate name entries.
            names = ', '.join(set(self.displayname.split(', ')))

            # Construct the suite name according to Launchpad/Soyuz
            # convention.
            pocket_suffix = pocketsuffix[self.pocket]
            if pocket_suffix:
                suite = '%s%s' % (self.distroseries.name, pocket_suffix)
            else:
                suite = self.distroseries.name

            subject = '[%s/%s] %s %s (%s)' % (
                self.distroseries.distribution.name, suite, names,
                self.displayversion, message.STATUS)

            if self.isPPA():
                subject = "[PPA %s] %s" % (
                    get_ppa_reference(self.archive), subject)
                attach_changes = False
            else:
                attach_changes = True

            self._sendMail(
                recipients, subject, body, dry_run, from_addr=from_addr,
                bcc=bcc, changesfile_content=changesfile_content,
                attach_changes=attach_changes)

        class NewMessage:
            """New message."""
            template = get_email_template('upload-new.txt')

            STATUS = "New"
            SUMMARY = summarystring
            CHANGESFILE = sanitize_string(
                ChangesFile.formatChangesComment(changes['Changes']))
            DISTRO = self.distroseries.distribution.title
            if announce_list:
                ANNOUNCE = 'Announcing to %s' % announce_list
            else:
                ANNOUNCE = 'No announcement sent'

        class UnapprovedMessage:
            """Unapproved message."""
            template = get_email_template('upload-accepted.txt')

            STATUS = "Waiting for approval"
            SUMMARY = summarystring + (
                    "\nThis upload awaits approval by a distro manager\n")
            CHANGESFILE = sanitize_string(
                ChangesFile.formatChangesComment(changes['Changes']))
            DISTRO = self.distroseries.distribution.title
            if announce_list:
                ANNOUNCE = 'Announcing to %s' % announce_list
            else:
                ANNOUNCE = 'No announcement sent'
            CHANGEDBY = ''
            ORIGIN = ''
            SIGNER = ''
            MAINTAINER = ''
            SPR_URL = ''

        class AcceptedMessage:
            """Accepted message."""
            template = get_email_template('upload-accepted.txt')

            STATUS = "Accepted"
            SUMMARY = summarystring
            CHANGESFILE = sanitize_string(
                ChangesFile.formatChangesComment(changes['Changes']))
            DISTRO = self.distroseries.distribution.title
            if announce_list:
                ANNOUNCE = 'Announcing to %s' % announce_list
            else:
                ANNOUNCE = 'No announcement sent'
            CHANGEDBY = ''
            ORIGIN = ''
            SIGNER = ''
            MAINTAINER = ''
            SPR_URL = ''

        class PPAAcceptedMessage:
            """PPA accepted message."""
            template = get_email_template('ppa-upload-accepted.txt')

            STATUS = "Accepted"
            SUMMARY = summarystring
            CHANGESFILE = guess_encoding(
                ChangesFile.formatChangesComment("".join(changes_lines)))

        class AnnouncementMessage:
            template = get_email_template('upload-announcement.txt')

            STATUS = "Accepted"
            SUMMARY = summarystring
            CHANGESFILE = sanitize_string(
                ChangesFile.formatChangesComment(changes['Changes']))
            CHANGEDBY = ''
            ORIGIN = ''
            SIGNER = ''
            MAINTAINER = ''
            SPR_URL = ''

        # The template is ready.  The remainder of this function deals with
        # whether to send a 'new' message, an acceptance message and/or an
        # announcement message.

        if self.status == PackageUploadStatus.NEW:
            # This is an unknown upload.
            do_sendmail(NewMessage)
            return

        # Unapproved uploads coming from an insecure policy only send
        # an acceptance message.
        if self.status == PackageUploadStatus.UNAPPROVED:
            # Only send an acceptance message.
            do_sendmail(UnapprovedMessage)
            return

        if self.isPPA():
            # PPA uploads receive an acceptance message.
            do_sendmail(PPAAcceptedMessage)
            return

        # Auto-approved uploads to backports skips the announcement,
        # they are usually processed with the sync policy.
        if self.pocket == PackagePublishingPocket.BACKPORTS:
            debug(self.logger, "Skipping announcement, it is a BACKPORT.")

            do_sendmail(AcceptedMessage)
            return

        # Auto-approved binary-only uploads to security skip the
        # announcement, they are usually processed with the security policy.
        if (self.pocket == PackagePublishingPocket.SECURITY
            and not self.contains_source):
            # We only send announcements if there is any source in the upload.
            debug(self.logger,
                "Skipping announcement, it is a binary upload to SECURITY.")
            do_sendmail(AcceptedMessage)
            return

        # Fallback, all the rest coming from insecure, secure and sync
        # policies should send an acceptance and an announcement message.
        do_sendmail(AcceptedMessage)

        # Don't send announcements for Debian auto sync uploads.
        if self.isAutoSyncUpload(changed_by_email=changes['Changed-By']):
            return

        if announce_list:
            if not self.signing_key:
                from_addr = None
            else:
                from_addr = guess_encoding(changes['Changed-By'])

            do_sendmail(
                AnnouncementMessage,
                recipients=[str(announce_list)],
                from_addr=from_addr,
                bcc="%s_derivatives@packages.qa.debian.org" %
                    self.displayname)

    def notify(self, announce_list=None, summary_text=None,
               changes_file_object=None, logger=None, dry_run=False,
               allow_unsigned=None, notify_success=True):
        """See `IPackageUpload`."""

        self.logger = logger

        # If this is a binary or mixed upload, we don't send *any* emails
        # provided it's not a rejection or a security upload:
        if(self.from_build and
           self.status != PackageUploadStatus.REJECTED and
           self.pocket != PackagePublishingPocket.SECURITY):
            debug(self.logger, "Not sending email; upload is from a build.")
            return

        # XXX julian 2007-05-11:
        # Requiring an open changesfile object is a bit ugly but it is
        # required because of several problems:
        # a) We don't know if the librarian has the file committed or not yet
        # b) Passing a ChangesFile object instead means that we get an
        #    unordered dictionary which can't be translated back exactly for
        #    the email's summary section.
        # For now, it's just easier to re-read the original file if the caller
        # requires us to do that instead of using the librarian's copy.
        changes, changes_lines = self._getChangesDict(
            changes_file_object, allow_unsigned=allow_unsigned)

        # "files" will contain a list of tuples of filename,component,section.
        # If files is empty, we don't need to send an email if this is not
        # a rejection.
        try:
            files = self._buildUploadedFilesList()
        except LanguagePackEncountered:
            # Don't send emails for language packs.
            return

        if not files and self.status != PackageUploadStatus.REJECTED:
            return

        summary = self._buildSummary(files)
        if summary_text:
            summary.append(summary_text)
        summarystring = "\n".join(summary)

        recipients = self._getRecipients(changes)

        # There can be no recipients if none of the emails are registered
        # in LP.
        if not recipients:
            debug(self.logger, "No recipients on email, not sending.")
            return

        # Make the content of the actual changes file available to the
        # various email generating/sending functions.
        if changes_file_object is not None:
            changesfile_content = changes_file_object.read()
        else:
            changesfile_content = 'No changes file content available'

        # If we need to send a rejection, do it now and return early.
        if self.status == PackageUploadStatus.REJECTED:
            self._sendRejectionNotification(
                recipients, changes_lines, changes, summary_text, dry_run,
                changesfile_content)
            return

        self._sendSuccessNotification(
            recipients, announce_list, changes_lines, changes, summarystring,
            dry_run, changesfile_content)

    def _getRecipients(self, changes):
        """Return a list of recipients for notification emails."""
        candidate_recipients = []
        debug(self.logger, "Building recipients list.")
        changer = self._emailToPerson(changes['Changed-By'])

        if self.signing_key:
            # This is a signed upload.
            signer = self.signing_key.owner
            candidate_recipients.append(signer)
        else:
            debug(self.logger,
                "Changes file is unsigned, adding changer as recipient")
            candidate_recipients.append(changer)

        if self.isPPA():
            # For PPAs, any person or team mentioned explicitly in the
            # ArchivePermissions as uploaders for the archive will also
            # get emailed.
            uploaders = [
                permission.person for permission in
                    self.archive.getUploadersForComponent()]
            candidate_recipients.extend(uploaders)

        # If this is not a PPA, we also consider maintainer and changed-by.
        if self.signing_key and not self.isPPA():
            maintainer = self._emailToPerson(changes['Maintainer'])
            if (maintainer and maintainer != signer and
                    maintainer.isUploader(self.distroseries.distribution)):
                debug(self.logger, "Adding maintainer to recipients")
                candidate_recipients.append(maintainer)

            if (changer and changer != signer and
                    changer.isUploader(self.distroseries.distribution)):
                debug(self.logger, "Adding changed-by to recipients")
                candidate_recipients.append(changer)

        # Now filter list of recipients for persons only registered in
        # Launchpad to avoid spamming the innocent.
        recipients = []
        for person in candidate_recipients:
            if person is None or person.preferredemail is None:
                continue
            recipient = format_address(person.displayname,
                person.preferredemail.email)
            debug(self.logger, "Adding recipient: '%s'" % recipient)
            recipients.append(recipient)

        return recipients

    # XXX julian 2007-05-21:
    # This method should really be IPersonSet.getByUploader but requires
    # some extra work to port safe_fix_maintainer to emailaddress.py and
    # then get nascent upload to use that.
    def _emailToPerson(self, fullemail):
        """Return an IPerson given an RFC2047 email address."""
        # The 2nd arg to s_f_m() doesn't matter as it won't fail since every-
        # thing will have already parsed at this point.
        (rfc822, rfc2047, name, email) = safe_fix_maintainer(
            fullemail, "email")
        person = getUtility(IPersonSet).getByEmail(email)
        return person

    def _isPersonUploader(self, person):
        """Return True if person is an uploader to the package's distro."""
        debug(self.logger, "Attempting to decide if %s is an uploader." % (
            person.displayname))
        uploader = person.isUploader(self.distroseries.distribution)
        debug(self.logger, "Decision: %s" % uploader)
        return uploader

    def _sendMail(
        self, to_addrs, subject, mail_text, dry_run, from_addr=None, bcc=None,
        changesfile_content=None, attach_changes=False):
        """Send an email to to_addrs with the given text and subject.

        :to_addrs: A list of email addresses to be used as recipients. Each
            email must be a valid ASCII str instance or a unicode one.
        :subject: The email's subject.
        :mail_text: The text body of the email. Unicode is preserved in the
            email.
        :dry_run: Whether or not an email should actually be sent. But
            please note that this flag is (largely) ignored.
        :from_addr: The email address to be used as the sender. Must be a
            valid ASCII str instance or a unicode one.  Defaults to the email
            for config.uploader.
        :bcc: Optional email Blind Carbon Copy address(es).
        :changesfile_content: The content of the actual changesfile.
        :attach_changes: A flag governing whether the original changesfile
            content shall be attached to the email.
        """
        extra_headers = {'X-Katie': 'Launchpad actually'}

        # XXX cprov 20071212: ideally we only need to check archive.purpose,
        # however the current code in uploadprocessor.py (around line 259)
        # temporarily transforms the primary-archive into a PPA one (w/o
        # setting a proper owner) in order to allow processing of a upload
        # to unknown PPA and subsequent rejection notification.

        # Include the 'X-Launchpad-PPA' header for PPA upload notfications
        # containing the PPA owner name.
        if (self.archive.is_ppa and self.archive.owner is not None):
            extra_headers['X-Launchpad-PPA'] = get_ppa_reference(self.archive)

        # Include a 'X-Launchpad-Component' header with the component and
        # the section of the source package uploaded in order to facilitate
        # filtering on the part of the email recipients.
        if self.sources:
            spr = self.my_source_package_release
            xlp_component_header = 'component=%s, section=%s' % (
                spr.component.name, spr.section.name)
            extra_headers['X-Launchpad-Component'] = xlp_component_header

        if from_addr is None:
            from_addr = format_address(
                config.uploader.default_sender_name,
                config.uploader.default_sender_address)

        # `sendmail`, despite handling unicode message bodies, can't
        # cope with non-ascii sender/recipient addresses, so ascii_smash
        # is used on all addresses.

        # All emails from here have a Bcc to the default recipient.
        bcc_text = format_address(
            config.uploader.default_recipient_name,
            config.uploader.default_recipient_address)
        if bcc:
            bcc_text = "%s, %s" % (bcc_text, bcc)
        extra_headers['Bcc'] = ascii_smash(bcc_text)

        recipients = ascii_smash(", ".join(to_addrs))
        if isinstance(from_addr, unicode):
            # ascii_smash only works on unicode strings.
            from_addr = ascii_smash(from_addr)
        else:
            from_addr.encode('ascii')

        if dry_run and self.logger is not None:
            self.logger.info("Would have sent a mail:")
            self.logger.info("  Subject: %s" % subject)
            self.logger.info("  Sender: %s" % from_addr)
            self.logger.info("  Recipients: %s" % recipients)
            self.logger.info("  Bcc: %s" % extra_headers['Bcc'])
            self.logger.info("  Body:")
            for line in mail_text.splitlines():
                self.logger.info(line)
        else:
            debug(self.logger, "Sent a mail:")
            debug(self.logger, "    Subject: %s" % subject)
            debug(self.logger, "    Recipients: %s" % recipients)
            debug(self.logger, "    Body:")
            for line in mail_text.splitlines():
                debug(self.logger, line)

            # Since we need to send the original changesfile as an
            # attachment the sendmail() method will be used as opposed to
            # simple_sendmail().
            message = MIMEMultipart()
            message['from'] = from_addr
            message['subject'] = subject
            message['to'] = recipients

            # Set the extra headers if any are present.
            for key, value in extra_headers.iteritems():
                message.add_header(key, value)

            # Add the email body.
            message.attach(MIMEText(
               sanitize_string(mail_text).encode('utf-8'), 'plain', 'utf-8'))

            if attach_changes:
                # Add the original changesfile as an attachment.
                if changesfile_content is not None:
                    changesfile_text = sanitize_string(changesfile_content)
                else:
                    changesfile_text = ("Sorry, changesfile not available.")

                attachment = MIMEText(
                    changesfile_text.encode('utf-8'), 'plain', 'utf-8')
                attachment.add_header(
                    'Content-Disposition',
                    'attachment; filename="changesfile"')
                message.attach(attachment)

            # And finally send the message.
            sendmail(message)

    @property
    def components(self):
        """See `IPackageUpload`."""
        existing_components = set()
        if self.contains_source:
            existing_components.add(self.sourcepackagerelease.component)
        else:
            # For builds we need to iterate through all its binaries
            # and collect each component.
            for build in self.builds:
                for binary in build.build.binarypackages:
                    existing_components.add(binary.component)
        return existing_components

    def overrideSource(self, new_component, new_section, allowed_components):
        """See `IPackageUpload`."""
        if not self.contains_source:
            return False

        if new_component is None and new_section is None:
            # Nothing needs overriding, bail out.
            return False

        for source in self.sources:
            if (new_component not in allowed_components or
                source.sourcepackagerelease.component not in
                    allowed_components):
                # The old or the new component is not in the list of
                # allowed components to override.
                raise QueueInconsistentStateError(
                    "No rights to override from %s to %s" % (
                        source.sourcepackagerelease.component.name,
                        new_component.name))
            source.sourcepackagerelease.override(
                component=new_component, section=new_section)

        # We override our own archive too, as it is used to create
        # the SPPH during publish().
        self.archive = self.distroseries.distribution.getArchiveByComponent(
            new_component.name)

        return True

    def overrideBinaries(self, new_component, new_section, new_priority,
                         allowed_components):
        """See `IPackageUpload`."""
        if not self.contains_build:
            return False

        if (new_component is None and new_section is None and
            new_priority is None):
            # Nothing needs overriding, bail out.
            return False

        for build in self.builds:
            for binarypackage in build.build.binarypackages:
                if (new_component not in allowed_components or
                    binarypackage.component not in allowed_components):
                    # The old or the new component is not in the list of
                    # allowed components to override.
                    raise QueueInconsistentStateError(
                        "No rights to override from %s to %s" % (
                            binarypackage.component.name,
                            new_component.name))
                binarypackage.override(
                    component=new_component,
                    section=new_section,
                    priority=new_priority)

        return bool(self.builds)


class PackageUploadBuild(SQLBase):
    """A Queue item's related builds."""
    implements(IPackageUploadBuild)

    _defaultOrder = ['id']

    packageupload = ForeignKey(
        dbName='packageupload',
        foreignKey='PackageUpload')

    build = ForeignKey(dbName='build', foreignKey='BinaryPackageBuild')

    def checkComponentAndSection(self):
        """See `IPackageUploadBuild`."""
        distroseries = self.packageupload.distroseries
        is_ppa = self.packageupload.archive.is_ppa
        is_delayed_copy = self.packageupload.is_delayed_copy

        for binary in self.build.binarypackages:
            component = binary.component

            if is_delayed_copy:
                # For a delayed copy the component will not yet have
                # had the chance to be overridden, so we'll check the value
                # that will be overridden by querying the ancestor in
                # the destination archive - if one is available.
                binary_name = binary.name
                ancestry = getUtility(IPublishingSet).getNearestAncestor(
                    package_name=binary_name,
                    archive=self.packageupload.archive,
                    distroseries=self.packageupload.distroseries, binary=True)

                if ancestry is not None:
                    component = ancestry.component

            if (not is_ppa and component not in
                distroseries.upload_components):
                # Only complain about non-PPA uploads.
                raise QueueBuildAcceptError(
                    'Component "%s" is not allowed in %s'
                    % (binary.component.name, distroseries.name))
            # At this point (uploads are already processed) sections are
            # guaranteed to exist in the DB. We don't care if sections are
            # not official.
            pass

    def publish(self, logger=None):
        """See `IPackageUploadBuild`."""
        # Determine the build's architecturetag
        build_archtag = self.build.distro_arch_series.architecturetag
        # Determine the target arch series.
        # This will raise NotFoundError if anything odd happens.
        target_das = self.packageupload.distroseries[build_archtag]
        debug(logger, "Publishing build to %s/%s/%s" % (
            target_das.distroseries.distribution.name,
            target_das.distroseries.name,
            build_archtag))

        # First up, publish everything in this build into that dar.
        published_binaries = []
        for binary in self.build.binarypackages:
            debug(
                logger, "... %s/%s (Arch %s)" % (
                binary.binarypackagename.name,
                binary.version,
                'Specific' if binary.architecturespecific else 'Independent',
                ))
            published_binaries.extend(
                getUtility(IPublishingSet).publishBinary(
                    archive=self.packageupload.archive,
                    binarypackagerelease=binary,
                    distroarchseries=target_das,
                    component=binary.component,
                    section=binary.section,
                    priority=binary.priority,
                    pocket=self.packageupload.pocket))
        return published_binaries


class PackageUploadSource(SQLBase):
    """A Queue item's related sourcepackagereleases."""

    implements(IPackageUploadSource)

    _defaultOrder = ['id']

    packageupload = ForeignKey(
        dbName='packageupload',
        foreignKey='PackageUpload')

    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease')

    def getSourceAncestry(self):
        """See `IPackageUploadSource`."""
        primary_archive = self.packageupload.distroseries.main_archive
        release_pocket = PackagePublishingPocket.RELEASE
        current_distroseries = self.packageupload.distroseries
        ancestry_locations = [
            (self.packageupload.archive, current_distroseries,
             self.packageupload.pocket),
            (primary_archive, current_distroseries, release_pocket),
            (primary_archive, None, release_pocket),
            ]

        ancestry = None
        for archive, distroseries, pocket in ancestry_locations:
            ancestries = archive.getPublishedSources(
                name=self.sourcepackagerelease.name,
                distroseries=distroseries, pocket=pocket,
                exact_match=True)
            try:
                ancestry = ancestries[0]
            except IndexError:
                continue
            break
        return ancestry

    def verifyBeforeAccept(self):
        """See `IPackageUploadSource`."""
        # Check for duplicate source version across all distroseries.
        conflict = getUtility(IPackageUploadSet).findSourceUpload(
            self.sourcepackagerelease.name,
            self.sourcepackagerelease.version,
            self.packageupload.archive,
            self.packageupload.distroseries.distribution)

        if conflict is not None:
            raise QueueInconsistentStateError(
                "The source %s is already accepted in %s/%s and you "
                "cannot upload the same version within the same "
                "distribution. You have to modify the source version "
                "and re-upload." % (
                    self.sourcepackagerelease.title,
                    conflict.distroseries.distribution.name,
                    conflict.distroseries.name))

    def verifyBeforePublish(self):
        """See `IPackageUploadSource`."""
        distribution = self.packageupload.distroseries.distribution
        # Check for duplicate filenames currently present in the archive.
        for source_file in self.sourcepackagerelease.files:
            try:
                published_file = distribution.getFileByName(
                    source_file.libraryfile.filename, binary=False,
                    archive=self.packageupload.archive)
            except NotFoundError:
                # NEW files are *OK*.
                continue

            filename = source_file.libraryfile.filename
            proposed_sha1 = source_file.libraryfile.content.sha1
            published_sha1 = published_file.content.sha1

            # Multiple orig(s) with the same content are fine.
            if source_file.is_orig:
                if proposed_sha1 == published_sha1:
                    continue
                raise QueueInconsistentStateError(
                    '%s is already published in archive for %s with a '
                    'different SHA1 hash (%s != %s)' % (
                    filename, self.packageupload.distroseries.name,
                    proposed_sha1, published_sha1))

            # Any dsc(s), targz(s) and diff(s) already present
            # are a very big problem.
            raise QueueInconsistentStateError(
                '%s is already published in archive for %s' % (
                filename, self.packageupload.distroseries.name))

    def checkComponentAndSection(self):
        """See `IPackageUploadSource`."""
        distroseries = self.packageupload.distroseries
        component = self.sourcepackagerelease.component

        if self.packageupload.is_delayed_copy:
            # For a delayed copy the component will not yet have
            # had the chance to be overridden, so we'll check the value
            # that will be overridden by querying the ancestor in
            # the destination archive - if one is available.
            source_name = self.sourcepackagerelease.name
            ancestry = getUtility(IPublishingSet).getNearestAncestor(
                package_name=source_name,
                archive=self.packageupload.archive,
                distroseries=self.packageupload.distroseries)

            if ancestry is not None:
                component = ancestry.component

        if (not self.packageupload.archive.is_ppa and
            component not in distroseries.upload_components):
            # Only complain about non-PPA uploads.
            raise QueueSourceAcceptError(
                'Component "%s" is not allowed in %s' % (component.name,
                                                         distroseries.name))

        # At this point (uploads are already processed) sections are
        # guaranteed to exist in the DB. We don't care if sections are
        # not official.
        pass

    def publish(self, logger=None):
        """See `IPackageUploadSource`."""
        # Publish myself in the distroseries pointed at by my queue item.
        debug(logger, "Publishing source %s/%s to %s/%s in the %s archive" % (
            self.sourcepackagerelease.name,
            self.sourcepackagerelease.version,
            self.packageupload.distroseries.distribution.name,
            self.packageupload.distroseries.name,
            self.packageupload.archive.name))

        return getUtility(IPublishingSet).newSourcePublication(
            archive=self.packageupload.archive,
            sourcepackagerelease=self.sourcepackagerelease,
            distroseries=self.packageupload.distroseries,
            component=self.sourcepackagerelease.component,
            section=self.sourcepackagerelease.section,
            pocket=self.packageupload.pocket)


class PackageUploadCustom(SQLBase):
    """A Queue item's related custom format uploads."""
    implements(IPackageUploadCustom)

    _defaultOrder = ['id']

    packageupload = ForeignKey(
        dbName='packageupload',
        foreignKey='PackageUpload')

    customformat = EnumCol(dbName='customformat', unique=False,
                           notNull=True, schema=PackageUploadCustomFormat)

    libraryfilealias = ForeignKey(dbName='libraryfilealias',
                                  foreignKey="LibraryFileAlias",
                                  notNull=True)

    def publish(self, logger=None):
        """See `IPackageUploadCustom`."""
        # This is a marker as per the comment in dbschema.py.
        ##CUSTOMFORMAT##
        # Essentially, if you alter anything to do with what custom formats
        # are, what their tags are, or anything along those lines, you should
        # grep for the marker in the source tree and fix it up in every place
        # so marked.
        debug(logger, "Publishing custom %s to %s/%s" % (
            self.packageupload.displayname,
            self.packageupload.distroseries.distribution.name,
            self.packageupload.distroseries.name))

        name = "publish_" + self.customformat.name
        method = getattr(self, name, None)
        if method is not None:
            method(logger)
        else:
            raise NotFoundError("Unable to find a publisher method for %s" % (
                self.customformat.name))

    def temp_filename(self):
        """See `IPackageUploadCustom`."""
        temp_dir = tempfile.mkdtemp()
        temp_file_name = os.path.join(
            temp_dir, self.libraryfilealias.filename)
        temp_file = file(temp_file_name, "wb")
        self.libraryfilealias.open()
        copy_and_close(self.libraryfilealias, temp_file)
        return temp_file_name

    def _publishCustom(self, action_method):
        """Publish custom formats.

        Publish Either an installer, an upgrader or a ddtp upload using the
        supplied action method.
        """
        temp_filename = self.temp_filename()
        full_suite_name = "%s%s" % (
            self.packageupload.distroseries.name,
            pocketsuffix[self.packageupload.pocket])
        try:
            # See the XXX near the import for getPubConfig.
            archive_config = getPubConfig(self.packageupload.archive)
            action_method(
                archive_config.archiveroot, temp_filename,
                full_suite_name)
        finally:
            shutil.rmtree(os.path.dirname(temp_filename))

    def publish_DEBIAN_INSTALLER(self, logger=None):
        """See `IPackageUploadCustom`."""
        # XXX cprov 2005-03-03: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from lp.archivepublisher.debian_installer import (
            process_debian_installer)

        self._publishCustom(process_debian_installer)

    def publish_DIST_UPGRADER(self, logger=None):
        """See `IPackageUploadCustom`."""
        # XXX cprov 2005-03-03: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from lp.archivepublisher.dist_upgrader import (
            process_dist_upgrader)

        self._publishCustom(process_dist_upgrader)

    def publish_DDTP_TARBALL(self, logger=None):
        """See `IPackageUploadCustom`."""
        # XXX cprov 2005-03-03: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from lp.archivepublisher.ddtp_tarball import (
            process_ddtp_tarball)

        self._publishCustom(process_ddtp_tarball)

    def publish_ROSETTA_TRANSLATIONS(self, logger=None):
        """See `IPackageUploadCustom`."""
        sourcepackagerelease = self.packageupload.sourcepackagerelease

        # Ignore translations not with main distribution purposes.
        if self.packageupload.archive.purpose not in MAIN_ARCHIVE_PURPOSES:
            debug(logger,
                  "Skipping translations since its purpose is not "
                  "in MAIN_ARCHIVE_PURPOSES.")
            return

        valid_pockets = (
            PackagePublishingPocket.RELEASE, PackagePublishingPocket.SECURITY,
            PackagePublishingPocket.UPDATES, PackagePublishingPocket.PROPOSED)
        valid_component_names = ('main', 'restricted')
        if (self.packageupload.pocket not in valid_pockets or
            sourcepackagerelease.component.name not in valid_component_names):
            # XXX: CarlosPerelloMarin 2006-02-16 bug=31665:
            # This should be implemented using a more general rule to accept
            # different policies depending on the distribution.
            # Ubuntu's MOTU told us that they are not able to handle
            # translations like we do in main. We are going to import only
            # packages in main.
            return

        # Set the importer to package creator.
        importer = sourcepackagerelease.creator

        # Attach the translation tarball. It's always published.
        try:
            sourcepackagerelease.attachTranslationFiles(
                self.libraryfilealias, True, importer=importer)
        except DownloadFailed:
            if logger is not None:
                debug(logger, "Unable to fetch %s to import it into Rosetta" %
                    self.libraryfilealias.http_url)

    def publish_STATIC_TRANSLATIONS(self, logger=None):
        """See `IPackageUploadCustom`."""
        # Static translations are not published.  Currently, they're
        # only exposed via webservice methods so that third parties can
        # retrieve them from the librarian.
        debug(logger, "Skipping publishing of static translations.")
        return

    def publish_META_DATA(self, logger=None):
        """See `IPackageUploadCustom`."""
        # In the future this could use the existing custom upload file
        # processing which deals with versioning, etc., but that's too
        # complicated for our needs right now.  Also, the existing code
        # assumes that everything is a tarball and tries to unpack it.

        archive = self.packageupload.archive
        # See the XXX near the import for getPubConfig.
        archive_config = getPubConfig(archive)
        dest_file = os.path.join(
            archive_config.metaroot, self.libraryfilealias.filename)
        if not os.path.isdir(archive_config.metaroot):
            os.makedirs(archive_config.metaroot, 0755)

        # At this point we now have a directory of the format:
        # <person_name>/meta/<ppa_name>
        # We're ready to copy the file out of the librarian into it.

        file_obj = file(dest_file, "wb")
        self.libraryfilealias.open()
        copy_and_close(self.libraryfilealias, file_obj)


class PackageUploadSet:
    """See `IPackageUploadSet`"""
    implements(IPackageUploadSet)

    def __iter__(self):
        """See `IPackageUploadSet`."""
        return iter(PackageUpload.select())

    def __getitem__(self, queue_id):
        """See `IPackageUploadSet`."""
        try:
            return PackageUpload.get(queue_id)
        except SQLObjectNotFound:
            raise NotFoundError(queue_id)

    def get(self, queue_id):
        """See `IPackageUploadSet`."""
        try:
            return PackageUpload.get(queue_id)
        except SQLObjectNotFound:
            raise NotFoundError(queue_id)

    def createDelayedCopy(self, archive, distroseries, pocket,
                          signing_key):
        """See `IPackageUploadSet`."""
        return PackageUpload(
            archive=archive, distroseries=distroseries, pocket=pocket,
            status=PackageUploadStatus.NEW, signing_key=signing_key)

    def findSourceUpload(self, name, version, archive, distribution):
        """See `IPackageUploadSet`."""
        # Avoiding circular imports.
        from lp.registry.model.distroseries import DistroSeries
        from lp.registry.model.sourcepackagename import SourcePackageName
        from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease

        store = IMasterStore(PackageUpload)
        origin = (
            PackageUpload,
            Join(DistroSeries,
                 DistroSeries.id == PackageUpload.distroseriesID),
            Join(PackageUploadSource,
                 PackageUploadSource.packageuploadID == PackageUpload.id),
            Join(SourcePackageRelease,
                 SourcePackageRelease.id ==
                     PackageUploadSource.sourcepackagereleaseID),
            Join(SourcePackageName,
                 SourcePackageName.id ==
                     SourcePackageRelease.sourcepackagenameID),
            )

        approved_status = (
            PackageUploadStatus.ACCEPTED,
            PackageUploadStatus.DONE,
            )
        conflicts = store.using(*origin).find(
            PackageUpload,
            PackageUpload.status.is_in(approved_status),
            PackageUpload.archive == archive,
            DistroSeries.distribution == distribution,
            SourcePackageRelease.version == version,
            SourcePackageName.name == name)

        return conflicts.one()

    def count(self, status=None, distroseries=None, pocket=None):
        """See `IPackageUploadSet`."""
        clauses = []
        if status:
            clauses.append("status=%s" % sqlvalues(status))

        if distroseries:
            clauses.append("distroseries=%s" % sqlvalues(distroseries))

        if pocket:
            clauses.append("pocket=%s" % sqlvalues(pocket))

        query = " AND ".join(clauses)
        return PackageUpload.select(query).count()

    def getAll(self, distroseries, created_since_date=None, status=None,
               archive=None, pocket=None, custom_type=None):
        """See `IPackageUploadSet`."""
        # XXX Julian 2009-07-02 bug=394645
        # This method is an incremental deprecation of
        # IDistroSeries.getQueueItems(). It's basically re-writing it
        # using Storm queries instead of SQLObject, but not everything
        # is implemented yet.  When it is, this comment and the old
        # method can be removed and call sites updated to use this one.
        store = Store.of(distroseries)

        def dbitem_tuple(item_or_list):
            if not isinstance(item_or_list, list):
                return (item_or_list,)
            else:
                return tuple(item_or_list)

        timestamp_query_clause = ()
        if created_since_date is not None:
            timestamp_query_clause = (
                PackageUpload.date_created > created_since_date,)

        status_query_clause = ()
        if status is not None:
            status = dbitem_tuple(status)
            status_query_clause = (PackageUpload.status.is_in(status),)

        archives = distroseries.distribution.getArchiveIDList(archive)
        archive_query_clause = (PackageUpload.archiveID.is_in(archives),)

        pocket_query_clause = ()
        if pocket is not None:
            pocket = dbitem_tuple(pocket)
            pocket_query_clause = (PackageUpload.pocket.is_in(pocket),)

        custom_type_query_clause = ()
        if custom_type is not None:
            custom_type = dbitem_tuple(custom_type)
            custom_type_query_clause = (
                PackageUpload.id == PackageUploadCustom.packageuploadID,
                PackageUploadCustom.customformat.is_in(custom_type))

        return store.find(
            PackageUpload,
            PackageUpload.distroseries == distroseries,
            *(status_query_clause + archive_query_clause +
              pocket_query_clause + timestamp_query_clause +
              custom_type_query_clause)).order_by(
                  Desc(PackageUpload.id)).config(distinct=True)

    def getBuildByBuildIDs(self, build_ids):
        """See `IPackageUploadSet`."""
        if build_ids is None or len(build_ids) == 0:
            return []
        return PackageUploadBuild.select("""
            PackageUploadBuild.build IN %s
            """ % sqlvalues(build_ids))

    def getSourceBySourcePackageReleaseIDs(self, spr_ids):
        """See `IPackageUploadSet`."""
        if spr_ids is None or len(spr_ids) == 0:
            return []
        return PackageUploadSource.select("""
            PackageUploadSource.sourcepackagerelease IN %s
            """ % sqlvalues(spr_ids))
