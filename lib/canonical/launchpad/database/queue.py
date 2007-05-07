# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'PackageUploadQueue',
    'DistroReleaseQueue',
    'DistroReleaseQueueBuild',
    'DistroReleaseQueueSource',
    'DistroReleaseQueueCustom',
    'DistroReleaseQueueSet',
    ]

import os
import shutil
import tempfile
from email import message_from_string

from zope.interface import implements
from sqlobject import (
    ForeignKey, SQLMultipleJoin, SQLObjectNotFound)

from canonical.launchpad.mail import sendmail
from canonical.archivepublisher.customupload import CustomUploadError
from canonical.archivepublisher.nascentuploadfile import 
    splitComponentAndSection
from canonical.archivepublisher.tagfiles import (
    parse_tagfile_lines, TagFileParseError)
from canonical.archivepublisher.template_messages import (
    rejection_template, new_template, accepted_template, announce_template)
from canonical.cachedproperty import cachedproperty
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import EnumCol
from canonical.encoding import (
    guess as guess_encoding, ascii_smash)
from canonical.config import config
from canonical.launchpad.interfaces import (
    IDistroReleaseQueue, IDistroReleaseQueueBuild, IDistroReleaseQueueSource,
    IDistroReleaseQueueCustom, NotFoundError, QueueStateWriteProtectedError,
    QueueInconsistentStateError, QueueSourceAcceptError, IPackageUploadQueue,
    QueueBuildAcceptError, IDistroReleaseQueueSet, pocketsuffix)
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)
from canonical.librarian.interfaces import DownloadFailed
from canonical.librarian.utils import copy_and_close
from canonical.lp.dbschema import (
    DistroReleaseQueueStatus, DistroReleaseQueueCustomFormat,
    PackagePublishingPocket, PackagePublishingStatus)

# There are imports below in DistroReleaseQueueCustom for various bits
# of the archivepublisher which cause circular import errors if they
# are placed here.


def debug(logger, msg):
    """Shorthand debug notation for publish() methods."""
    if logger is not None:
        logger.debug(msg)

class PackageUploadQueue:

    implements(IPackageUploadQueue)

    def __init__(self, distrorelease, status):
        self.distrorelease = distrorelease
        self.status = status


class DistroReleaseQueue(SQLBase):
    """A Queue item for Lucille."""
    implements(IDistroReleaseQueue)

    _defaultOrder = ['id']

    status = EnumCol(dbName='status', unique=False, notNull=True,
                     default=DistroReleaseQueueStatus.NEW,
                     schema=DistroReleaseQueueStatus)

    distrorelease = ForeignKey(dbName="distrorelease",
                               foreignKey='DistroRelease')

    pocket = EnumCol(dbName='pocket', unique=False, notNull=True,
                     schema=PackagePublishingPocket)

    # XXX: this is NULLable. Fix sampledata?
    changesfile = ForeignKey(dbName='changesfile',
                             foreignKey="LibraryFileAlias")

    signing_key = ForeignKey(foreignKey='GPGKey', dbName='signing_key',
                             notNull=False)

    # Join this table to the DistroReleaseQueueBuild and the
    # DistroReleaseQueueSource objects which are related.

    # XXX julian 2007-05-06
    # sources and builds should not be SQLMultipleJoin, there is only
    # ever one of each at most.
    sources = SQLMultipleJoin('DistroReleaseQueueSource',
                              joinColumn='distroreleasequeue')
    builds = SQLMultipleJoin('DistroReleaseQueueBuild',
                             joinColumn='distroreleasequeue')

    # Also the custom files associated with the build.
    customfiles = SQLMultipleJoin('DistroReleaseQueueCustom',
                                  joinColumn='distroreleasequeue')


    def _set_status(self, value):
        """Directly write on 'status' is forbidden.

        Force user to use the provided machine-state methods.
        Raises QueueStateWriteProtectedError.
        """
        # XXX: bug #29663: this is a bit evil, but does the job. Andrew
        # has suggested using immutable=True in the column definition.
        #   -- kiko, 2006-01-25
        # allow 'status' write only in creation process.
        if self._SO_creating:
            self._SO_set_status(value)
            return
        # been fascist
        raise QueueStateWriteProtectedError(
            'Directly write on queue status is forbidden use the '
            'provided methods to set it.')

    def setNew(self):
        """See IDistroReleaseQueue."""
        if self.status == DistroReleaseQueueStatus.NEW:
            raise QueueInconsistentStateError(
                'Queue item already new')
        self._SO_set_status(DistroReleaseQueueStatus.NEW)

    def setUnapproved(self):
        """See IDistroReleaseQueue."""
        if self.status == DistroReleaseQueueStatus.UNAPPROVED:
            raise QueueInconsistentStateError(
                'Queue item already unapproved')
        self._SO_set_status(DistroReleaseQueueStatus.UNAPPROVED)

    def setAccepted(self):
        """See IDistroReleaseQueue."""
        # Explode if something wrong like warty/RELEASE pass through
        # NascentUpload/UploadPolicies checks
        assert self.distrorelease.canUploadToPocket(self.pocket)

        if self.status == DistroReleaseQueueStatus.ACCEPTED:
            raise QueueInconsistentStateError(
                'Queue item already accepted')

        for source in self.sources:
            # If two queue items have the same (name, version) pair,
            # then there is an inconsistency.  Check the accepted & done
            # queue items for each distro release for such duplicates
            # and raise an exception if any are found.
            # See bug #31038 & #62976 for details.
            for distrorelease in self.distrorelease.distribution:
                if distrorelease.getQueueItems(
                    status=[DistroReleaseQueueStatus.ACCEPTED,
                            DistroReleaseQueueStatus.DONE],
                    name=source.sourcepackagerelease.name,
                    version=source.sourcepackagerelease.version,
                    exact_match=True).count() > 0:
                    raise QueueInconsistentStateError(
                        'This sourcepackagerelease is already accepted in %s.'
                        % distrorelease.name)

            # if something goes wrong we will raise an exception
            # (QueueSourceAcceptError) before setting any value.
            # Mask the error with state-machine default exception
            try:
                source.checkComponentAndSection()
            except QueueSourceAcceptError, info:
                raise QueueInconsistentStateError(info)

        for build in self.builds:
            # as before, but for QueueBuildAcceptError
            try:
                build.checkComponentAndSection()
            except QueueBuildAcceptError, info:
                raise QueueInconsistentStateError(info)

        # if the previous checks applied and pass we do set the value
        self._SO_set_status(DistroReleaseQueueStatus.ACCEPTED)

    def setDone(self):
        """See IDistroReleaseQueue."""
        if self.status == DistroReleaseQueueStatus.DONE:
            raise QueueInconsistentStateError(
                'Queue item already done')
        self._SO_set_status(DistroReleaseQueueStatus.DONE)

    def setRejected(self):
        """See IDistroReleaseQueue."""
        if self.status == DistroReleaseQueueStatus.REJECTED:
            raise QueueInconsistentStateError(
                'Queue item already rejected')
        self._SO_set_status(DistroReleaseQueueStatus.REJECTED)

    # XXX cprov 20060314: following properties should be redesigned to
    # reduce the duplicated code.
    @cachedproperty
    def containsSource(self):
        """See IDistroReleaseQueue."""
        return self.sources

    @cachedproperty
    def containsBuild(self):
        """See IDistroReleaseQueue."""
        return self.builds

    @cachedproperty
    def _customFormats(self):
        """Return the custom upload formats contained in this upload."""
        return [custom.customformat for custom in self.customfiles]

    @cachedproperty
    def containsInstaller(self):
        """See IDistroReleaseQueue."""
        return (DistroReleaseQueueCustomFormat.DEBIAN_INSTALLER
                in self._customFormats)

    @cachedproperty
    def containsTranslation(self):
        """See IDistroReleaseQueue."""
        return (DistroReleaseQueueCustomFormat.ROSETTA_TRANSLATIONS
                in self._customFormats)

    @cachedproperty
    def containsUpgrader(self):
        """See IDistroReleaseQueue."""
        return (DistroReleaseQueueCustomFormat.DIST_UPGRADER
                in self._customFormats)

    @cachedproperty
    def containsDdtp(self):
        """See IDistroReleaseQueue."""
        return (DistroReleaseQueueCustomFormat.DDTP_TARBALL
                in self._customFormats)

    @cachedproperty
    def datecreated(self):
        """See IDistroReleaseQueue."""
        return self.changesfile.content.datecreated

    @cachedproperty
    def displayname(self):
        """See IDistroReleaseQueue"""
        names = []
        for queue_source in self.sources:
            names.append(queue_source.sourcepackagerelease.name)
        for queue_build in  self.builds:
            names.append(queue_build.build.sourcepackagerelease.name)
        for queue_custom in self.customfiles:
            names.append(queue_custom.libraryfilealias.filename)
        return ",".join(names)

    @cachedproperty
    def displayarchs(self):
        """See IDistroReleaseQueue"""
        archs = []
        for queue_source in self.sources:
            archs.append('source')
        for queue_build in self.builds:
            archs.append(queue_build.build.distroarchrelease.architecturetag)
        for queue_custom in self.customfiles:
            archs.append(queue_custom.customformat.title)
        return ",".join(archs)

    @cachedproperty
    def displayversion(self):
        """See IDistroReleaseQueue"""
        if self.sources:
            return self.sources[0].sourcepackagerelease.version
        if self.builds:
            return self.builds[0].build.sourcepackagerelease.version
        if self.customfiles:
            return '-'

    @cachedproperty
    def sourcepackagerelease(self):
        """The source package release related to this queue item.

        This is currently heuristic but may be more easily calculated later.
        """
        assert self.sources or self.builds
        if self.sources:
            return self.sources[0].sourcepackagerelease
        if self.builds:
            return self.builds[0].build.sourcepackagerelease

    def realiseUpload(self, logger=None):
        """See IDistroReleaseQueue."""
        assert self.status == DistroReleaseQueueStatus.ACCEPTED
        # Explode if something wrong like warty/RELEASE pass through
        # NascentUpload/UploadPolicies checks
        assert self.distrorelease.canUploadToPocket(self.pocket)

        # In realising an upload we first load all the sources into
        # the publishing tables, then the binaries, then we attempt
        # to publish the custom objects.
        for queue_source in self.sources:
            queue_source.publish(logger)
        for queue_build in self.builds:
            queue_build.publish(logger)
        for customfile in self.customfiles:
            try:
                customfile.publish(logger)
            except CustomUploadError, e:
                logger.error("Queue item ignored: %s" % e)
                return

        self.setDone()

    def addSource(self, spr):
        """See IDistroReleaseQueue."""
        return DistroReleaseQueueSource(distroreleasequeue=self,
                                        sourcepackagerelease=spr)

    def addBuild(self, build):
        """See IDistroReleaseQueue."""
        return DistroReleaseQueueBuild(distroreleasequeue=self, build=build)

    def addCustom(self, library_file, custom_type):
        """See IDistroReleaseQueue."""
        return DistroReleaseQueueCustom(distroreleasequeue=self,
                                        libraryfilealias=library_file,
                                        customformat=custom_type)

    def notify(self, sender, recipients, announcelist):
        """See IDistroReleaseQueue."""

        # Get the changes file from the librarian and parse the tags to
        # a dictionary.  This can throw exceptions but since the tag file
        # already will have parsed elsewhere we don't need to worry about that
        # here.  Any exceptions from the librarian can be left to the caller.
        changeslines = changesfile.read()
        changes = parse_tagfile_lines(changeslines)

        summary = []
        is_new = False # Is set to True if any part of the upload is new.
        files = changes['files'].strip().split("\n")

        # Build a summary string and bail out early if this is an upload
        # for the translations section.
        for fileline in files:
            digest, size, component_and_section, priority, filename = (
                fileline.strip().split())
            try:
                distrorelease.distribution.getFileByName(filename)
                summary.append("NEW: %s" % filename)
                is_new = True
            except NotFoundError:
                summary.append(" OK: %s" % filename)
                if filename.endswith("dsc"):
                    component, section = splitComponentAndSection(
                        component_and_section)
                    if section == 'translations':
                        # Uploads targetted to translations should not
                        # generate any emails
                        logger.debug(
                            "Skipping acceptance and announcement, it is a "
                            "language-package upload.")
                        return
                    summary.append("     -> Component: %s Section: %s" % (
                        component, section))`
        summarystring = "\n".join(summary)

        interpolations = {
            "MAINTAINERFROM": sender,
            "SENDER": sender,
            "CHANGES": changesfile.filename,
            "SUMMARY": summarystring,
            "CHANGESFILE": guess_encoding(changeslines),
            "DISTRO": distrorelease.distribution.title,
            "DISTRORELEASE": distrorelease.name,
            "ANNOUNCE": announcelist,
            "SOURCE": sourcefile.sourcepackagerelease.name,
            "VERSION": sourcefile.sourcepackagerelease.version,
            "ARCH": changes['architecture'],
            "RECIPIENT": ", ".join(recipients),
            "DEFAULT_RECIPIENT": "%s <%s>" % (
                config.uploader.default_recipient_name,
                config.uploader.default_recipient_address),

        }

        # The template is ready.  The remainder of this function deals with
        # whether to send a 'new' message, an acceptance message and/or an
        # announce message.

        if is_new:
            # This is an unknown upload.
            _sendMail(new_template % interpolations)
            return

        # Unapproved uploads coming from an insecure policy only sends
        # an acceptance message.
        if not self.status == DistroReleaseQueueStatus.APPROVED:
            # Only send an acceptance message
            interpolations["SUMMARY"] += (
                "\nThis upload awaits approval by a distro manager\n")
            _sendMail(accept_template % interpolations)
            return

        # Auto-approved uploads to backports skips the announcement,
        # they are usually processed with the sync policy.
        if self.pocket == PackagePublishingPocket.BACKPORTS:
            logger.debug("Skipping announcement, it is a BACKPORT.")
            _sendMail(accept_template % interpolations)
            return

        # Auto-approved binary uploads to security skips the announcement,
        # they are usually processed with the security policy.
        if (self.pocket == PackagePublishingPocket.SECURITY
            and self.containsBuild):
            logger.debug(
                "Skipping announcement, it is a binary upload to SECURITY.")
            _sendMail(accept_template % interpolations)
            return

        # Fallback, all the rest coming from insecure, secure and sync
        # policies should send an acceptance and an announcement message.
        _sendMail(accept_template % interpolations)
        _sendMail(announce_template % interpolations)

    def _sendMail(self,mail_text):
        mail_message = message_from_string(ascii_smash(mail_text))
        sendmail(mail_message)

        logger.debug("Sent a mail:")
        logger.debug("    Subject: %s" % mail_message['Subject'])
        logger.debug("    Recipients: %s" % mail_message['To'])
        logger.debug("    Body:")
        for line in mail_message.get_payload().splitlines():
            logger.debug(line)

class DistroReleaseQueueBuild(SQLBase):
    """A Queue item's related builds (for Lucille)."""
    implements(IDistroReleaseQueueBuild)

    _defaultOrder = ['id']

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    build = ForeignKey(dbName='build', foreignKey='Build')

    def checkComponentAndSection(self):
        """See IDistroReleaseQueueBuild."""
        distrorelease = self.distroreleasequeue.distrorelease
        for binary in self.build.binarypackages:
            if binary.component not in distrorelease.components:
                raise QueueBuildAcceptError(
                    'Component "%s" is not allowed in %s'
                    % (binary.component.name, distrorelease.name))
            if binary.section not in distrorelease.sections:
                raise QueueBuildAcceptError(
                    'Section "%s" is not allowed in %s' % (binary.section.name,
                                                           distrorelease.name))

    def publish(self, logger=None):
        """See IDistroReleaseQueueBuild."""
        # Determine the build's architecturetag.
        build_archtag = self.build.distroarchrelease.architecturetag
        # Determine the target arch release.
        # This will raise NotFoundError if anything odd happens.
        target_dar = self.distroreleasequeue.distrorelease[build_archtag]
        debug(logger, "Publishing build to %s/%s/%s" % (
            target_dar.distrorelease.distribution.name,
            target_dar.distrorelease.name,
            build_archtag))
        # And get the other distroarchreleases
        other_dars = set(self.distroreleasequeue.distrorelease.architectures)
        other_dars = other_dars - set([target_dar])
        # First up, publish everything in this build into that dar.
        published_binaries = []
        for binary in self.build.binarypackages:
            target_dars = set([target_dar])
            if not binary.architecturespecific:
                target_dars = target_dars.union(other_dars)
                debug(logger, "... %s/%s (Arch Independent)" % (
                    binary.binarypackagename.name,
                    binary.version))
            else:
                debug(logger, "... %s/%s (Arch Specific)" % (
                    binary.binarypackagename.name,
                    binary.version))
            for each_target_dar in target_dars:
                # XXX: dsilvers: 20051020: What do we do about embargoed
                # binaries here? bug 3408
                sbpph = SecureBinaryPackagePublishingHistory(
                    binarypackagerelease=binary,
                    distroarchrelease=each_target_dar,
                    component=binary.component,
                    section=binary.section,
                    priority=binary.priority,
                    status=PackagePublishingStatus.PENDING,
                    datecreated=UTC_NOW,
                    pocket=self.distroreleasequeue.pocket,
                    embargo=False
                    )
                published_binaries.append(sbpph)
        return published_binaries


class DistroReleaseQueueSource(SQLBase):
    """A Queue item's related sourcepackagereleases (for Lucille)."""
    implements(IDistroReleaseQueueSource)

    _defaultOrder = ['id']

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease'
        )

    def checkComponentAndSection(self):
        """See IDistroReleaseQueueSource."""
        distrorelease = self.distroreleasequeue.distrorelease
        component = self.sourcepackagerelease.component
        section = self.sourcepackagerelease.section

        if component not in distrorelease.components:
            raise QueueSourceAcceptError(
                'Component "%s" is not allowed in %s' % (component.name,
                                                         distrorelease.name))

        if section not in distrorelease.sections:
            raise QueueSourceAcceptError(
                'Section "%s" is not allowed in %s' % (section.name,
                                                       distrorelease.name))

    def publish(self, logger=None):
        """See IDistroReleaseQueueSource."""
        # Publish myself in the distrorelease pointed at by my queue item.
        # XXX: dsilvers: 20051020: What do we do here to support embargoed
        # sources? bug 3408
        debug(logger, "Publishing source %s/%s to %s/%s" % (
            self.sourcepackagerelease.name,
            self.sourcepackagerelease.version,
            self.distroreleasequeue.distrorelease.distribution.name,
            self.distroreleasequeue.distrorelease.name))

        return SecureSourcePackagePublishingHistory(
            distrorelease=self.distroreleasequeue.distrorelease,
            sourcepackagerelease=self.sourcepackagerelease,
            component=self.sourcepackagerelease.component,
            section=self.sourcepackagerelease.section,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=self.distroreleasequeue.pocket,
            embargo=False)


class DistroReleaseQueueCustom(SQLBase):
    """A Queue item's related custom format uploads."""
    implements(IDistroReleaseQueueCustom)

    _defaultOrder = ['id']

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    customformat = EnumCol(dbName='customformat', unique=False,
                           notNull=True, schema=DistroReleaseQueueCustomFormat)

    libraryfilealias = ForeignKey(dbName='libraryfilealias',
                                  foreignKey="LibraryFileAlias",
                                  notNull=True)

    def publish(self, logger=None):
        """See IDistroReleaseQueueCustom."""
        # This is a marker as per the comment in dbschema.py.
        ##CUSTOMFORMAT##
        # Essentially, if you alter anything to do with what custom formats
        # are, what their tags are, or anything along those lines, you should
        # grep for the marker in the source tree and fix it up in every place
        # so marked.
        debug(logger, "Publishing custom %s to %s/%s" % (
            self.distroreleasequeue.displayname,
            self.distroreleasequeue.distrorelease.distribution.name,
            self.distroreleasequeue.distrorelease.name))

        name = "publish_" + self.customformat.name
        method = getattr(self, name, None)
        if method is not None:
            method(logger)
        else:
            raise NotFoundError("Unable to find a publisher method for %s" % (
                self.customformat.name))

    def temp_filename(self):
        """See IDistroReleaseQueueCustom."""
        temp_dir = tempfile.mkdtemp()
        temp_file_name = os.path.join(temp_dir, self.libraryfilealias.filename)
        temp_file = file(temp_file_name, "wb")
        self.libraryfilealias.open()
        copy_and_close(self.libraryfilealias, temp_file)
        return temp_file_name

    @property
    def archive_config(self):
        """See IDistroReleaseQueueCustom."""
        # XXX cprov 20050303: use the Zope Component Lookup to instantiate
        # the object in question and avoid circular imports
        from canonical.archivepublisher.config import Config as ArchiveConfig
        distrorelease = self.distroreleasequeue.distrorelease
        return ArchiveConfig(distrorelease.distribution)

    def _publishCustom(self, action_method):
        """Publish custom formats.

        Publish Either an installer, an upgrader or a ddtp upload using the
        supplied action method.
        """
        temp_filename = self.temp_filename()
        full_suite_name = "%s%s" % (
            self.distroreleasequeue.distrorelease.name,
            pocketsuffix[self.distroreleasequeue.pocket])
        try:
            action_method(
                self.archive_config.archiveroot, temp_filename,
                full_suite_name)
        finally:
            shutil.rmtree(os.path.dirname(temp_filename))

    def publish_DEBIAN_INSTALLER(self, logger=None):
        """See IDistroReleaseQueueCustom."""
        # XXX cprov 20050303: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from canonical.archivepublisher.debian_installer import (
            process_debian_installer)

        self._publishCustom(process_debian_installer)

    def publish_DIST_UPGRADER(self, logger=None):
        """See IDistroReleaseQueueCustom."""
        # XXX cprov 20050303: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from canonical.archivepublisher.dist_upgrader import (
            process_dist_upgrader)

        self._publishCustom(process_dist_upgrader)

    def publish_DDTP_TARBALL(self, logger=None):
        """See IDistroReleaseQueueCustom."""
        # XXX cprov 20050303: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from canonical.archivepublisher.ddtp_tarball import (
            process_ddtp_tarball)

        self._publishCustom(process_ddtp_tarball)

    def publish_ROSETTA_TRANSLATIONS(self, logger=None):
        """See IDistroReleaseQueueCustom."""
        # XXX: dsilvers: 20051115: We should be able to get a
        # sourcepackagerelease directly.
        sourcepackagerelease = (
            self.distroreleasequeue.builds[0].build.sourcepackagerelease)

        valid_pockets = (PackagePublishingPocket.RELEASE,
            PackagePublishingPocket.SECURITY, PackagePublishingPocket.UPDATES,
            PackagePublishingPocket.PROPOSED)
        if (self.distroreleasequeue.pocket not in valid_pockets or
            sourcepackagerelease.component.name != 'main'):
            # XXX: CarlosPerelloMarin 20060216 This should be implemented
            # using a more general rule to accept different policies depending
            # on the distribution. See bug #31665 for more details.
            # Ubuntu's MOTU told us that they are not able to handle
            # translations like we do in main. We are going to import only
            # packages in main.
            return

        # Attach the translation tarball. It's always published.
        try:
            sourcepackagerelease.attachTranslationFiles(
                self.libraryfilealias, True)
        except DownloadFailed:
            if logger is not None:
                debug(logger, "Unable to fetch %s to import it into Rosetta" %
                    self.libraryfilealias.http_url)


class DistroReleaseQueueSet:
    """See IDistroReleaseQueueSet"""
    implements(IDistroReleaseQueueSet)

    def __iter__(self):
        """See IDistroReleaseQueueSet."""
        return iter(DistroReleaseQueue.select())

    def __getitem__(self, queue_id):
        """See IDistroReleaseQueueSet."""
        try:
            return DistroReleaseQueue.get(queue_id)
        except SQLObjectNotFound:
            raise NotFoundError(queue_id)

    def get(self, queue_id):
        """See IDistroReleaseQueueSet."""
        try:
            return DistroReleaseQueue.get(queue_id)
        except SQLObjectNotFound:
            raise NotFoundError(queue_id)

    def count(self, status=None, distrorelease=None, pocket=None):
        """See IDistroReleaseQueueSet."""
        clauses = []
        if status:
            clauses.append("status=%s" % sqlvalues(status))

        if distrorelease:
            clauses.append("distrorelease=%s" % sqlvalues(distrorelease))

        if pocket:
            clauses.append("pocket=%s" % sqlvalues(pocket))

        query = " AND ".join(clauses)

        return DistroReleaseQueue.select(query).count()

