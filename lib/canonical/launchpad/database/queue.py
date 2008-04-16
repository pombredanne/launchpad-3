# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
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

import os
import shutil
import tempfile

from zope.component import getUtility
from zope.interface import implements
from sqlobject import (
    ForeignKey, SQLMultipleJoin, SQLObjectNotFound)

from canonical.archivepublisher.customupload import CustomUploadError
from canonical.archiveuploader.tagfiles import parse_tagfile_lines
from canonical.archiveuploader.utils import safe_fix_maintainer
from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import EnumCol
from canonical.encoding import (
    guess as guess_encoding, ascii_smash)
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory,
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory)
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces import (
    ArchivePurpose, IComponentSet, ILaunchpadCelebrities, IPackageUpload,
    IPackageUploadBuild, IPackageUploadSource, IPackageUploadCustom,
    IPackageUploadQueue, IPackageUploadSet, IPersonSet, NotFoundError,
    PackagePublishingPocket, PackagePublishingStatus, PackageUploadStatus,
    PackageUploadCustomFormat, pocketsuffix, QueueBuildAcceptError,
    QueueInconsistentStateError, QueueStateWriteProtectedError,
    QueueSourceAcceptError, SourcePackageFileType)
from canonical.launchpad.mail import (
    format_address, signed_message_from_string, simple_sendmail)
from canonical.launchpad.scripts.processaccepted import (
    close_bugs_for_queue_item)
from canonical.librarian.interfaces import DownloadFailed
from canonical.librarian.utils import copy_and_close

# There are imports below in PackageUploadCustom for various bits
# of the archivepublisher which cause circular import errors if they
# are placed here.


def debug(logger, msg):
    """Shorthand debug notation for publish() methods."""
    if logger is not None:
        logger.debug(msg)


class PackageUploadQueue:

    implements(IPackageUploadQueue)

    def __init__(self, distroseries, status):
        self.distroseries = distroseries
        self.status = status


class LanguagePackEncountered(Exception):
    """Thrown when not wanting to email notifications for language packs."""


class PackageUpload(SQLBase):
    """A Queue item for Lucille."""
    implements(IPackageUpload)

    _defaultOrder = ['id']

    status = EnumCol(dbName='status', unique=False, notNull=True,
                     default=PackageUploadStatus.NEW,
                     schema=PackageUploadStatus)

    distroseries = ForeignKey(dbName="distroseries",
                               foreignKey='DistroSeries')

    pocket = EnumCol(dbName='pocket', unique=False, notNull=True,
                     schema=PackagePublishingPocket)

    # XXX: kiko 2007-02-10: This is NULLable. Fix sampledata?
    changesfile = ForeignKey(dbName='changesfile',
                             foreignKey="LibraryFileAlias")

    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)

    signing_key = ForeignKey(foreignKey='GPGKey', dbName='signing_key',
                             notNull=False)

    # XXX julian 2007-05-06:
    # Sources and builds should not be SQLMultipleJoin, there is only
    # ever one of each at most.

    # Join this table to the PackageUploadBuild and the
    # PackageUploadSource objects which are related.
    sources = SQLMultipleJoin('PackageUploadSource',
                              joinColumn='packageupload')
    builds = SQLMultipleJoin('PackageUploadBuild',
                             joinColumn='packageupload')

    # Also the custom files associated with the build.
    customfiles = SQLMultipleJoin('PackageUploadCustom',
                                  joinColumn='packageupload')


    def _set_status(self, value):
        """Directly write on 'status' is forbidden.

        Force user to use the provided machine-state methods.
        Raises QueueStateWriteProtectedError.
        """
        # XXX: kiko 2006-01-25 bug=29663:
        # This is a bit evil, but does the job. Andrew
        # has suggested using immutable=True in the column definition.

        # allow 'status' write only in creation process.
        if self._SO_creating:
            self._SO_set_status(value)
            return
        # been fascist
        raise QueueStateWriteProtectedError(
            'Directly write on queue status is forbidden use the '
            'provided methods to set it.')

    def setNew(self):
        """See `IPackageUpload`."""
        if self.status == PackageUploadStatus.NEW:
            raise QueueInconsistentStateError(
                'Queue item already new')
        self._SO_set_status(PackageUploadStatus.NEW)

    def setUnapproved(self):
        """See `IPackageUpload`."""
        if self.status == PackageUploadStatus.UNAPPROVED:
            raise QueueInconsistentStateError(
                'Queue item already unapproved')
        self._SO_set_status(PackageUploadStatus.UNAPPROVED)

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

        for build in self.builds:
            # as before, but for QueueBuildAcceptError
            try:
                build.checkComponentAndSection()
            except QueueBuildAcceptError, info:
                raise QueueInconsistentStateError(info)

        # if the previous checks applied and pass we do set the value
        self._SO_set_status(PackageUploadStatus.ACCEPTED)

    def setDone(self):
        """See `IPackageUpload`."""
        if self.status == PackageUploadStatus.DONE:
            raise QueueInconsistentStateError(
                'Queue item already done')
        self._SO_set_status(PackageUploadStatus.DONE)

    def setRejected(self):
        """See `IPackageUpload`."""
        if self.status == PackageUploadStatus.REJECTED:
            raise QueueInconsistentStateError(
                'Queue item already rejected')
        self._SO_set_status(PackageUploadStatus.REJECTED)

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

    def acceptFromUploader(self, changesfile_path, logger=None):
        """See `IPackageUpload`."""
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
        pub_source.createMissingBuilds(logger=logger)
        self._closeBugs(changesfile_path, logger)

    def acceptFromQueue(self, announce_list, logger=None, dry_run=False):
        """See `IPackageUpload`."""
        self.setAccepted()
        self.notify(announce_list=announce_list, logger=logger,
                    dry_run=dry_run)
        self.syncUpdate()

        # If this is a single source upload we can create the
        # publishing records now so that the user doesn't have to
        # wait for a publisher cycle (which calls process-accepted
        # to do this).
        if self._isSingleSourceUpload():
            [pub_source] = self.realiseUpload()
            pub_source.createMissingBuilds(ignore_pas=True)

        # When accepting packages, we must also check the changes file
        # for bugs to close automatically.
        close_bugs_for_queue_item(self)

    def rejectFromQueue(self, logger=None, dry_run=False):
        """See `IPackageUpload`."""
        self.setRejected()
        self.notify(logger=logger, dry_run=dry_run)
        self.syncUpdate()

    def _isSingleSourceUpload(self):
        """Return True if this upload contains only a single source."""
        return ((self.sources.count() == 1) and
                (self.builds.count() == 0) and
                (self.customfiles.count() == 0))

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

    def _is_auto_sync_upload(self, changed_by_email):
        """Return True if this is a (Debian) auto sync upload.

        Sync uploads are source-only, unsigned and not targeted to
        the security pocket.  The Changed-By field is also the Katie
        user (archive@ubuntu.com).
        """
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
    def datecreated(self):
        """See `IPackageUpload`."""
        return self.changesfile.content.datecreated

    @cachedproperty
    def displayname(self):
        """See `IPackageUpload`"""
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
        """See `IPackageUpload`"""
        archs = []
        for queue_source in self.sources:
            archs.append('source')
        for queue_build in self.builds:
            archs.append(queue_build.build.distroarchseries.architecturetag)
        for queue_custom in self.customfiles:
            archs.append(queue_custom.customformat.title)
        return ",".join(archs)

    @cachedproperty
    def displayversion(self):
        """See `IPackageUpload`"""
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
        assert self.sources or self.builds, ('No source available.')
        if self.sources:
            return self.sources[0].sourcepackagerelease
        if self.builds:
            return self.builds[0].build.sourcepackagerelease

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
                return

        self.setDone()

        return publishing_records

    def addSource(self, spr):
        """See `IPackageUpload`."""
        return PackageUploadSource(
            packageupload=self,
            sourcepackagerelease=spr.id
            )

    def addBuild(self, build):
        """See `IPackageUpload`."""
        return PackageUploadBuild(
            packageupload=self,
            build=build.id
            )

    def addCustom(self, library_file, custom_type):
        """See `IPackageUpload`."""
        return PackageUploadCustom(
            packageupload=self,
            libraryfilealias=library_file.id,
            customformat=custom_type
            )

    def isPPA(self):
        """See `IPackageUpload`."""
        return self.archive.purpose == ArchivePurpose.PPA

    def _stripPgpSignature(self, changes_lines):
        """Strip any PGP signature from the supplied changes lines."""
        text = "".join(changes_lines)
        signed_message = signed_message_from_string(text)
        return signed_message.signedContent.splitlines(True)

    def _getChangesDict(self, changes_file_object=None):
        """Return a dictionary with changes file tags in it."""
        changes_lines = None
        if changes_file_object is None:
            changes_file_object = self.changesfile
            changes_lines = self.changesfile.read().splitlines(True)
        else:
            changes_lines = changes_file_object.readlines()

        unsigned = not self.signing_key
        changes = parse_tagfile_lines(changes_lines, allow_unsigned=unsigned)

        if self.isPPA():
            # Leaving the PGP signature on a package uploaded to a PPA
            # leaves the possibility of someone hijacking the notification
            # and uploading to the Ubuntu archive as the signer.
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
                files.extend(
                    [(bpf.libraryfile.filename,'','') for bpf in bpr.files])

        if self.customfiles:
            files.extend(
                [(file.libraryfilealias.filename,'','')
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

    def _sendRejectionNotification(self, recipients, changes_lines,
                                   summary_text, dry_run):
        """Send a rejection email."""

        default_recipient = "%s <%s>" % (
            config.uploader.default_recipient_name,
            config.uploader.default_recipient_address)
        if not recipients:
            recipients = [default_recipient]

        interpolations = {
            "SUMMARY": summary_text,
            "CHANGESFILE": guess_encoding("".join(changes_lines)),
        }
        debug(self.logger, "Sending rejection email.")
        if self.isPPA():
            rejection_template = get_email_template(
                'ppa-upload-rejection.txt')
        else:
            rejection_template = get_email_template('upload-rejection.txt')
        self._sendMail(
            recipients,
            "%s rejected" % self.changesfile.filename,
            rejection_template % interpolations,
            dry_run)

    def _sendSuccessNotification(self, recipients, announce_list,
            changes_lines, changes, summarystring, dry_run):
        """Send a success email."""

        def do_sendmail(message, recipients=recipients, from_addr=None,
                        bcc=None):
            """Perform substitutions on a template and send the email."""
            body = message.template % message.__dict__
            subject = "%s: %s %s (%s)" % (
                message.STATUS, self.displayname, self.displayversion,
                self.displayarchs)
            if self.isPPA():
                subject = "[PPA %s] " % self.archive.owner.name + subject
            self._sendMail(recipients, subject, body, dry_run,
                           from_addr=from_addr, bcc=bcc)

        class NewMessage:
            """New message."""
            template = get_email_template('upload-new.txt')

            STATUS = "New"
            SUMMARY = summarystring
            CHANGESFILE = guess_encoding("".join(changes_lines))
            DISTRO = self.distroseries.distribution.title
            ANNOUNCE = announce_list

        class UnapprovedMessage:
            """Unapproved message."""
            template = get_email_template('upload-accepted.txt')

            STATUS = "Waiting for approval"
            SUMMARY = summarystring + (
                    "\nThis upload awaits approval by a distro manager\n")
            CHANGESFILE = guess_encoding("".join(changes_lines))
            DISTRO = self.distroseries.distribution.title
            ANNOUNCE = announce_list

        class AcceptedMessage:
            """Accepted message."""
            template = get_email_template('upload-accepted.txt')

            STATUS = "Accepted"
            SUMMARY = summarystring
            CHANGESFILE = guess_encoding("".join(changes_lines))
            DISTRO = self.distroseries.distribution.title
            ANNOUNCE = announce_list

        class PPAAcceptedMessage:
            """PPA accepted message."""
            template = get_email_template('ppa-upload-accepted.txt')

            STATUS = "Accepted"
            SUMMARY = summarystring
            CHANGESFILE = guess_encoding("".join(changes_lines))

        class AnnouncementMessage:
            template = get_email_template('upload-announcement.txt')

            STATUS = "Accepted"
            SUMMARY = summarystring
            CHANGESFILE = guess_encoding("".join(changes_lines))


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
        if self._is_auto_sync_upload(changed_by_email=changes['changed-by']):
            return

        if announce_list:
            if not self.signing_key:
                from_addr = None
            else:
                from_addr = guess_encoding(changes['changed-by'])

            do_sendmail(
                AnnouncementMessage,
                recipients=[str(announce_list)],
                from_addr=from_addr,
                bcc="%s_derivatives@packages.qa.debian.org" %
                    self.displayname)

    def notify(self, announce_list=None, summary_text=None,
               changes_file_object=None, logger=None, dry_run=False):
        """See `IPackageUpload`."""

        self.logger = logger

        # If this is a binary or mixed upload, we don't send *any* emails
        # provided it's not a rejection or a security upload:
        if(self.contains_build and
           self.status != PackageUploadStatus.REJECTED and
           self.pocket != PackagePublishingPocket.SECURITY):
            debug(self.logger, "Not sending email, upload contains binaries.")
            return

        # Get the changes file from the librarian and parse the tags to
        # a dictionary.  This can throw exceptions but since the tag file
        # already will have parsed elsewhere we don't need to worry about that
        # here.  Any exceptions from the librarian can be left to the caller.

        # XXX julian 2007-05-11:
        # Requiring an open changesfile object is a bit ugly but it is
        # required because of several problems:
        # a) We don't know if the librarian has the file committed or not yet
        # b) Passing a ChangesFile object instead means that we get an
        #    unordered dictionary which can't be translated back exactly for
        #    the email's summary section.
        # For now, it's just easier to re-read the original file if the caller
        # requires us to do that instead of using the librarian's copy.
        changes, changes_lines = self._getChangesDict(changes_file_object)

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
            debug(self.logger,"No recipients on email, not sending.")
            return

        # If we need to send a rejection, do it now and return early.
        if self.status == PackageUploadStatus.REJECTED:
            self._sendRejectionNotification(
                recipients, changes_lines, summary_text, dry_run)
            return

        self._sendSuccessNotification(
            recipients, announce_list, changes_lines, changes, summarystring,
            dry_run)

    def _getRecipients(self, changes):
        """Return a list of recipients for notification emails."""
        candidate_recipients = []
        debug(self.logger, "Building recipients list.")
        changer = self._emailToPerson(changes['changed-by'])

        if self.signing_key:
            # This is a signed upload.
            signer = self.signing_key.owner
            candidate_recipients.append(signer)
        else:
            debug(self.logger,
                "Changes file is unsigned, adding changer as recipient")
            candidate_recipients.append(changer)

        # PPA uploads only email the uploader but for everything else
        # we consider maintainer and changed-by also.
        if self.signing_key and not self.isPPA():
            maintainer = self._emailToPerson(changes['maintainer'])
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

    def _sendMail(self, to_addrs, subject, mail_text, dry_run,
                  from_addr=None, bcc=None):
        """Send an email to to_addrs with the given text and subject.

        :from_addr: The email address to be used as the sender.  Must be a
                    valid ASCII str instance or a unicode one.
                    Defaults to the email for config.uploader.
        :to_addrs: A list of email addresses to be used as recipients.  Each
                   email must be a valid ASCII str instance or a unicode one.
        :subject: The email's subject.
        :mail_text: The text body of the email.  Unicode is preserved in the
                    email.
        :bcc: Optional email Blind Carbon Copy address(es).
        """
        extra_headers = { 'X-Katie' : 'Launchpad actually' }

        # XXX cprov 20071212: ideally we only need to check archive.purpose,
        # however the current code in uploadprocessor.py (around line 259)
        # temporarily transforms the primary-archive into a PPA one (w/o
        # setting a proper owner) in order to allow processing of a upload
        # to unknown PPA and subsequent rejection notification.

        # Include the 'X-Launchpad-PPA' header for PPA upload notfications
        # containing the PPA owner name.
        if (self.archive.purpose == ArchivePurpose.PPA and
            self.archive.owner):
            extra_headers['X-Launchpad-PPA'] = self.archive.owner.name

        if from_addr is None:
            from_addr = format_address(
                config.uploader.default_sender_name,
                config.uploader.default_sender_address)

        # `simple_sendmail`, despite handling unicode message bodies, can't
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

            simple_sendmail(
                from_addr,
                recipients,
                subject,
                mail_text,
                extra_headers
            )


class PackageUploadBuild(SQLBase):
    """A Queue item's related builds (for Lucille)."""
    implements(IPackageUploadBuild)

    _defaultOrder = ['id']

    packageupload = ForeignKey(
        dbName='packageupload',
        foreignKey='PackageUpload'
        )

    build = ForeignKey(dbName='build', foreignKey='Build')

    def checkComponentAndSection(self):
        """See `IPackageUploadBuild`."""
        distroseries = self.packageupload.distroseries
        for binary in self.build.binarypackages:
            if binary.component not in distroseries.upload_components:
                raise QueueBuildAcceptError(
                    'Component "%s" is not allowed in %s'
                    % (binary.component.name, distroseries.name))
            if binary.section not in distroseries.sections:
                raise QueueBuildAcceptError(
                    'Section "%s" is not allowed in %s' %
                        (binary.section.name,
                         distroseries.name))

    def publish(self, logger=None):
        """See `IPackageUploadBuild`."""
        # Determine the build's architecturetag
        build_archtag = self.build.distroarchseries.architecturetag
        # Determine the target arch series.
        # This will raise NotFoundError if anything odd happens.
        target_dar = self.packageupload.distroseries[build_archtag]
        debug(logger, "Publishing build to %s/%s/%s" % (
            target_dar.distroseries.distribution.name,
            target_dar.distroseries.name,
            build_archtag))
        # And get the other distroarchseriess
        other_dars = set(self.packageupload.distroseries.architectures)
        other_dars = other_dars - set([target_dar])
        # First up, publish everything in this build into that dar.
        published_binaries = []
        main_component = getUtility(IComponentSet)['main']
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
                # XXX: dsilvers 2005-10-20 bug=3408:
                # What do we do about embargoed binaries here?
                if self.packageupload.archive.is_ppa:
                    # We override PPA to always publish in the main component.
                    component = main_component
                else:
                    component = binary.component

                sbpph = SecureBinaryPackagePublishingHistory(
                    binarypackagerelease=binary,
                    distroarchseries=each_target_dar,
                    component=component,
                    section=binary.section,
                    priority=binary.priority,
                    status=PackagePublishingStatus.PENDING,
                    datecreated=UTC_NOW,
                    pocket=self.packageupload.pocket,
                    embargo=False,
                    archive=self.packageupload.archive
                    )
                bpph = BinaryPackagePublishingHistory.get(sbpph.id)
                published_binaries.append(bpph)
        return published_binaries


class PackageUploadSource(SQLBase):
    """A Queue item's related sourcepackagereleases (for Lucille)."""
    implements(IPackageUploadSource)

    _defaultOrder = ['id']

    packageupload = ForeignKey(
        dbName='packageupload',
        foreignKey='PackageUpload'
        )

    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease'
        )

    def verifyBeforeAccept(self):
        """See `IPackageUploadSource`."""
        # Check for duplicate source version across all distroseries.
        for distroseries in self.packageupload.distroseries.distribution:
            uploads = distroseries.getQueueItems(
                status=[PackageUploadStatus.ACCEPTED,
                        PackageUploadStatus.DONE],
                name=self.sourcepackagerelease.name,
                version=self.sourcepackagerelease.version,
                archive=self.packageupload.archive,
                exact_match=True)
            if uploads.count() > 0:
                raise QueueInconsistentStateError(
                    "The source %s is already accepted in %s/%s and you "
                    "cannot upload the same version within the same "
                    "distribution. You have to modify the source version "
                    "and re-upload." % (
                    self.sourcepackagerelease.title,
                    distroseries.distribution.name,
                    distroseries.name))

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
            if source_file.filetype == SourcePackageFileType.ORIG:
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
        section = self.sourcepackagerelease.section

        if component not in distroseries.upload_components:
            raise QueueSourceAcceptError(
                'Component "%s" is not allowed in %s' % (component.name,
                                                         distroseries.name))

        if section not in distroseries.sections:
            raise QueueSourceAcceptError(
                'Section "%s" is not allowed in %s' % (section.name,
                                                       distroseries.name))

    def publish(self, logger=None):
        """See `IPackageUploadSource`."""
        # Publish myself in the distroseries pointed at by my queue item.
        # XXX: dsilvers: 2005-10-20 bug=3408:
        # What do we do here to support embargoed sources?
        debug(logger, "Publishing source %s/%s to %s/%s" % (
            self.sourcepackagerelease.name,
            self.sourcepackagerelease.version,
            self.packageupload.distroseries.distribution.name,
            self.packageupload.distroseries.name))

        if self.packageupload.archive.is_ppa:
            # We override PPA to always publish in the main component.
            component = getUtility(IComponentSet)['main']
        else:
            component = self.sourcepackagerelease.component

        sspph = SecureSourcePackagePublishingHistory(
            distroseries=self.packageupload.distroseries,
            sourcepackagerelease=self.sourcepackagerelease,
            component=component,
            section=self.sourcepackagerelease.section,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=self.packageupload.pocket,
            embargo=False,
            archive=self.packageupload.archive)
        return SourcePackagePublishingHistory.get(sspph.id)


class PackageUploadCustom(SQLBase):
    """A Queue item's related custom format uploads."""
    implements(IPackageUploadCustom)

    _defaultOrder = ['id']

    packageupload = ForeignKey(
        dbName='packageupload',
        foreignKey='PackageUpload'
        )

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

    @property
    def archive_config(self):
        """See `IPackageUploadCustom`."""
        archive = self.packageupload.archive
        return archive.getPubConfig()

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
            action_method(
                self.archive_config.archiveroot, temp_filename,
                full_suite_name)
        finally:
            shutil.rmtree(os.path.dirname(temp_filename))

    def publish_DEBIAN_INSTALLER(self, logger=None):
        """See `IPackageUploadCustom`."""
        # XXX cprov 2005-03-03: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from canonical.archivepublisher.debian_installer import (
            process_debian_installer)

        self._publishCustom(process_debian_installer)

    def publish_DIST_UPGRADER(self, logger=None):
        """See `IPackageUploadCustom`."""
        # XXX cprov 2005-03-03: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from canonical.archivepublisher.dist_upgrader import (
            process_dist_upgrader)

        self._publishCustom(process_dist_upgrader)

    def publish_DDTP_TARBALL(self, logger=None):
        """See `IPackageUploadCustom`."""
        # XXX cprov 2005-03-03: We need to use the Zope Component Lookup
        # to instantiate the object in question and avoid circular imports
        from canonical.archivepublisher.ddtp_tarball import (
            process_ddtp_tarball)

        self._publishCustom(process_ddtp_tarball)

    def publish_ROSETTA_TRANSLATIONS(self, logger=None):
        """See `IPackageUploadCustom`."""
        # XXX: dsilvers 2005-11-15: We should be able to get a
        # sourcepackagerelease directly.
        sourcepackagerelease = (
            self.packageupload.builds[0].build.sourcepackagerelease)

        # Ignore translation coming from PPA.
        if self.packageupload.isPPA():
            debug(logger, "Skipping translations since it is a PPA.")
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

        # Attach the translation tarball. It's always published.
        try:
            sourcepackagerelease.attachTranslationFiles(
                self.libraryfilealias, True)
        except DownloadFailed:
            if logger is not None:
                debug(logger, "Unable to fetch %s to import it into Rosetta" %
                    self.libraryfilealias.http_url)


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
