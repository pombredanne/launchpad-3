# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Notification for uploads and copies."""

__metaclass__ = type

__all__ = [
    'notify',
    ]


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from canonical.config import config
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import (
    format_address,
    sendmail,
    )
from canonical.launchpad.webapp import canonical_url
from lp.archivepublisher.utils import get_ppa_reference
from lp.archiveuploader.changesfile import ChangesFile
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.services.encoding import (
    ascii_smash,
    guess as guess_encoding,
    )
from lp.soyuz.enums import PackageUploadStatus


def notification(blamer, changesfile, archive, distroseries, pocket, action,
                 actor=None, reason=None):
    pass


def notify_spr_less(blamer, upload_path, changesfiles, reason):
    pass


def notify(packageupload, announce_list=None, summary_text=None,
       changes_file_object=None, logger=None, dry_run=False,
       allow_unsigned=None):
    """See `IPackageUpload`."""

    packageupload.logger = logger

    # If this is a binary or mixed upload, we don't send *any* emails
    # provided it's not a rejection or a security upload:
    if(packageupload.from_build and
       packageupload.status != PackageUploadStatus.REJECTED and
       packageupload.pocket != PackagePublishingPocket.SECURITY):
        debug(
            packageupload.logger,
            "Not sending email; upload is from a build.")
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
    changes, changes_lines = packageupload._getChangesDict(
        changes_file_object, allow_unsigned=allow_unsigned)

    # "files" will contain a list of tuples of filename,component,section.
    # If files is empty, we don't need to send an email if this is not
    # a rejection.
    try:
        files = _buildUploadedFilesList(packageupload)
    except LanguagePackEncountered:
        # Don't send emails for language packs.
        return

    if not files and packageupload.status != PackageUploadStatus.REJECTED:
        return

    summary = _buildSummary(packageupload, files)
    if summary_text:
        summary.append(summary_text)
    summarystring = "\n".join(summary)

    recipients = _getRecipients(packageupload, changes)

    # There can be no recipients if none of the emails are registered
    # in LP.
    if not recipients:
        debug(packageupload.logger, "No recipients on email, not sending.")
        return

    # Make the content of the actual changes file available to the
    # various email generating/sending functions.
    if changes_file_object is not None:
        changesfile_content = changes_file_object.read()
    else:
        changesfile_content = 'No changes file content available'

    # If we need to send a rejection, do it now and return early.
    if packageupload.status == PackageUploadStatus.REJECTED:
        _sendRejectionNotification(
            packageupload, recipients, changes_lines, changes, summary_text,
            dry_run, changesfile_content)
        return

    _sendSuccessNotification(
        packageupload, recipients, announce_list, changes_lines, changes,
        summarystring, dry_run, changesfile_content)


def _sendSuccessNotification(
    packageupload, recipients, announce_list, changes_lines, changes,
    summarystring, dry_run, changesfile_content):
    """Send a success email."""

    def do_sendmail(message, recipients=recipients, from_addr=None,
                    bcc=None):
        """Perform substitutions on a template and send the email."""
        _handleCommonBodyContent(packageupload, message, changes)
        body = message.template % message.__dict__

        # Weed out duplicate name entries.
        names = ', '.join(set(packageupload.displayname.split(', ')))

        # Construct the suite name according to Launchpad/Soyuz
        # convention.
        pocket_suffix = pocketsuffix[packageupload.pocket]
        if pocket_suffix:
            suite = '%s%s' % (packageupload.distroseries.name, pocket_suffix)
        else:
            suite = packageupload.distroseries.name

        subject = '[%s/%s] %s %s (%s)' % (
            packageupload.distroseries.distribution.name, suite, names,
            packageupload.displayversion, message.STATUS)

        if packageupload.isPPA():
            subject = "[PPA %s] %s" % (
                get_ppa_reference(packageupload.archive), subject)
            attach_changes = False
        else:
            attach_changes = True

        _sendMail(
            packageupload, recipients, subject, body, dry_run,
            from_addr=from_addr, bcc=bcc,
            changesfile_content=changesfile_content,
            attach_changes=attach_changes)

    class NewMessage:
        """New message."""
        template = get_email_template('upload-new.txt')

        STATUS = "New"
        SUMMARY = summarystring
        CHANGESFILE = sanitize_string(
            ChangesFile.formatChangesComment(changes['Changes']))
        DISTRO = packageupload.distroseries.distribution.title
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
        DISTRO = packageupload.distroseries.distribution.title
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
        DISTRO = packageupload.distroseries.distribution.title
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

    if packageupload.status == PackageUploadStatus.NEW:
        # This is an unknown upload.
        do_sendmail(NewMessage)
        return

    # Unapproved uploads coming from an insecure policy only send
    # an acceptance message.
    if packageupload.status == PackageUploadStatus.UNAPPROVED:
        # Only send an acceptance message.
        do_sendmail(UnapprovedMessage)
        return

    if packageupload.isPPA():
        # PPA uploads receive an acceptance message.
        do_sendmail(PPAAcceptedMessage)
        return

    # Auto-approved uploads to backports skips the announcement,
    # they are usually processed with the sync policy.
    if packageupload.pocket == PackagePublishingPocket.BACKPORTS:
        debug(
            packageupload.logger, "Skipping announcement, it is a BACKPORT.")

        do_sendmail(AcceptedMessage)
        return

    # Auto-approved binary-only uploads to security skip the
    # announcement, they are usually processed with the security policy.
    if (packageupload.pocket == PackagePublishingPocket.SECURITY
        and not packageupload.contains_source):
        # We only send announcements if there is any source in the upload.
        debug(packageupload.logger,
            "Skipping announcement, it is a binary upload to SECURITY.")
        do_sendmail(AcceptedMessage)
        return

    # Fallback, all the rest coming from insecure, secure and sync
    # policies should send an acceptance and an announcement message.
    do_sendmail(AcceptedMessage)

    # Don't send announcements for Debian auto sync uploads.
    if packageupload.isAutoSyncUpload(changed_by_email=changes['Changed-By']):
        return

    if announce_list:
        if not packageupload.signing_key:
            from_addr = None
        else:
            from_addr = guess_encoding(changes['Changed-By'])

        do_sendmail(
            AnnouncementMessage,
            recipients=[str(announce_list)],
            from_addr=from_addr,
            bcc="%s_derivatives@packages.qa.debian.org" %
                packageupload.displayname)


def _sendRejectionNotification(
    packageupload, recipients, changes_lines, changes, summary_text, dry_run,
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

    debug(packageupload.logger, "Sending rejection email.")
    if packageupload.isPPA():
        message = PPARejectedMessage
        attach_changes = False
    else:
        message = RejectedMessage
        attach_changes = True

    _handleCommonBodyContent(packageupload, message, changes)
    if summary_text is None:
        message.SUMMARY = 'Rejected by archive administrator.'

    body = message.template % message.__dict__

    subject = "%s rejected" % packageupload.changesfile.filename
    if packageupload.isPPA():
        subject = "[PPA %s] %s" % (
            get_ppa_reference(packageupload.archive), subject)

    _sendMail(
        packageupload, recipients, subject, body, dry_run,
        changesfile_content=changesfile_content,
        attach_changes=attach_changes)


def _sendMail(
    packageupload, to_addrs, subject, mail_text, dry_run, from_addr=None,
    bcc=None, changesfile_content=None, attach_changes=False):
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
    if (
        packageupload.archive.is_ppa and
        packageupload.archive.owner is not None):
        extra_headers['X-Launchpad-PPA'] = get_ppa_reference(
            packageupload.archive)

    # Include a 'X-Launchpad-Component' header with the component and
    # the section of the source package uploaded in order to facilitate
    # filtering on the part of the email recipients.
    if packageupload.sources:
        spr = packageupload.my_source_package_release
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

    if dry_run and packageupload.logger is not None:
        packageupload.logger.info("Would have sent a mail:")
        packageupload.logger.info("  Subject: %s" % subject)
        packageupload.logger.info("  Sender: %s" % from_addr)
        packageupload.logger.info("  Recipients: %s" % recipients)
        packageupload.logger.info("  Bcc: %s" % extra_headers['Bcc'])
        packageupload.logger.info("  Body:")
        for line in mail_text.splitlines():
            packageupload.logger.info(line)
    else:
        debug(packageupload.logger, "Sent a mail:")
        debug(packageupload.logger, "    Subject: %s" % subject)
        debug(packageupload.logger, "    Recipients: %s" % recipients)
        debug(packageupload.logger, "    Body:")
        for line in mail_text.splitlines():
            debug(packageupload.logger, line)

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


def _handleCommonBodyContent(packageupload, message, changes):
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
    if packageupload.signing_key is not None:
        # This is a signed upload.
        signer = packageupload.signing_key.owner

        signer_name = sanitize_string(signer.displayname)
        signer_email = sanitize_string(signer.preferredemail.email)

        signer_signature = '%s <%s>' % (signer_name, signer_email)

        if changed_by != signer_signature:
            message.SIGNER = '\nSigned-By: %s' % signer_signature

    # Add the debian 'Origin:' field if present.
    if changes.get('Origin') is not None:
        message.ORIGIN = '\nOrigin: %s' % changes['Origin']

    if packageupload.sources or packageupload.builds:
        message.SPR_URL = canonical_url(
            packageupload.my_source_package_release)


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


def debug(logger, msg):
    """Shorthand debug notation for publish() methods."""
    if logger is not None:
        logger.debug(msg)


def _getRecipients(packageupload, changes):
    """Return a list of recipients for notification emails."""
    candidate_recipients = []
    debug(packageupload.logger, "Building recipients list.")
    changer = packageupload._emailToPerson(changes['Changed-By'])

    if packageupload.signing_key:
        # This is a signed upload.
        signer = packageupload.signing_key.owner
        candidate_recipients.append(signer)
    else:
        debug(packageupload.logger,
            "Changes file is unsigned, adding changer as recipient")
        candidate_recipients.append(changer)

    if packageupload.isPPA():
        # For PPAs, any person or team mentioned explicitly in the
        # ArchivePermissions as uploaders for the archive will also
        # get emailed.
        uploaders = [
            permission.person for permission in
                packageupload.archive.getUploadersForComponent()]
        candidate_recipients.extend(uploaders)

    # If this is not a PPA, we also consider maintainer and changed-by.
    if packageupload.signing_key and not packageupload.isPPA():
        maintainer = packageupload._emailToPerson(changes['Maintainer'])
        if (maintainer and maintainer != signer and
                maintainer.isUploader(
                    packageupload.distroseries.distribution)):
            debug(packageupload.logger, "Adding maintainer to recipients")
            candidate_recipients.append(maintainer)

        if (changer and changer != signer and
                changer.isUploader(packageupload.distroseries.distribution)):
            debug(packageupload.logger, "Adding changed-by to recipients")
            candidate_recipients.append(changer)

    # Now filter list of recipients for persons only registered in
    # Launchpad to avoid spamming the innocent.
    recipients = []
    for person in candidate_recipients:
        if person is None or person.preferredemail is None:
            continue
        recipient = format_address(person.displayname,
            person.preferredemail.email)
        debug(packageupload.logger, "Adding recipient: '%s'" % recipient)
        recipients.append(recipient)

    return recipients


def _buildUploadedFilesList(packageupload):
    """Return a list of tuples of (filename, component, section).

    Component and section are only set where the file is a source upload.
    If an empty list is returned, it means there are no files.
    Raises LanguagePackRejection if a language pack is detected.
    No emails should be sent for language packs.
    """
    files = []
    if packageupload.contains_source:
        [source] = packageupload.sources
        spr = source.sourcepackagerelease
        # Bail out early if this is an upload for the translations
        # section.
        if spr.section.name == 'translations':
            debug(packageupload.logger,
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
    for build in packageupload.builds:
        for bpr in build.build.binarypackages:
            files.extend([
                (bpf.libraryfile.filename, '', '') for bpf in bpr.files])

    if packageupload.customfiles:
        files.extend(
            [(file.libraryfilealias.filename, '', '')
            for file in packageupload.customfiles])

    return files


def _buildSummary(packageupload, files):
    """Build a summary string based on the files present in the upload."""
    summary = []
    for filename, component, section in files:
        if packageupload.status == PackageUploadStatus.NEW:
            summary.append("NEW: %s" % filename)
        else:
            summary.append(" OK: %s" % filename)
            if filename.endswith("dsc"):
                summary.append("     -> Component: %s Section: %s" % (
                    component, section))
    return summary


class LanguagePackEncountered(Exception):
    """Thrown when not wanting to email notifications for language packs."""
