# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Notification for uploads and copies."""

__metaclass__ = type

__all__ = [
    'notify',
    ]


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import (
    format_address,
    sendmail,
    )
from canonical.launchpad.webapp import canonical_url
from lp.archivepublisher.utils import get_ppa_reference
from lp.archiveuploader.changesfile import ChangesFile
from lp.archiveuploader.utils import safe_fix_maintainer
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.encoding import (
    ascii_smash,
    guess as guess_encoding,
    )
from lp.soyuz.enums import PackageUploadStatus


def notification(blamer, spr, archive, distroseries, pocket, action,
                 actor=None, reason=None):
    pass


def notify_spr_less(blamer, changes_file_path, changes, reason, logger=None):
    ignored, filename = os.path.split(changes_file_path)
    subject = '%s rejected' % filename
    information = {
        'SUMMARY': reason,
        'CHANGESFILE': '',
        'DATE': '',
        'CHANGEDBY': '',
        'MAINTAINER': '',
        'SIGNER': '',
        'ORIGIN': '',
    }
    template = get_email_template('upload-rejection.txt')
    body = template % information
    from_addr = format_address(
        config.uploader.default_sender_name,
        config.uploader.default_sender_address)
    changedby = changes.get('Changed-By')
    logger.debug("Building recipients list.")
    recipients = ''
    if changedby is not None:
        changedby_person = _emailToPerson(changedby)
        if (
            changedby_person is not None and
            changedby_person.preferredemail is not None):
                recipients = format_address(changedby_person.displayname,
                    changedby_person.preferredemail.email)
    if recipients == '':
        recipients = "%s <%s>" % (
            config.uploader.default_recipient_name,
            config.uploader.default_recipient_address)
    extra_headers = {'X-Katie': 'Launchpad actually'}
    logger.debug("Sending rejection email.")
    send_message(
        subject, from_addr, recipients, extra_headers, body,
        attach_changes=False, logger=logger)


def get_template(archive, action):
    """Return the appropriate e-mail template."""
    template_name = 'upload-'
    if action in ('new', 'accepted', 'announcement'):
        template_name += action
    elif action == 'unapproved':
        template_name += 'accepted'
    elif action == 'rejected':
        template_name += 'rejection'
    if archive.is_ppa:
        template_name = 'ppa-%s' % template_name
    template_name += '.txt'
    return get_email_template(template_name)


def get_status(action):
    action_descriptions = {
        'new': 'New',
        'unapproved': 'Waiting for approval',
        'rejected': 'Rejected',
        'accepted': 'Accepted',
        'announcement': 'Accepted'
        }
    return action_descriptions[action]


def calculate_subject(spr, bprs, customfiles, archive, distroseries,
                      pocket, action):
    """Return the e-mail subject for the notification."""
    suite = distroseries.getSuite(pocket)
    names = set([spr.name])
    for bpr in bprs:
        names.add(bpr.build.source_package_release.name)
    for custom in customfiles:
        names.add(custom.libraryfilealias.filename)
    name_str = ', '.join(names)
    subject = '[%s/%s] %s %s (%s)' % (
        distroseries.distribution.name, suite, name_str, spr.version,
        get_status(action))
    if archive.is_ppa:
        subject = '[PPA %s] %s' % (get_ppa_reference(archive), subject)
    return subject


def notify(packageupload, announce_list=None, summary_text=None,
       changes_file_object=None, logger=None, dry_run=False,
       allow_unsigned=None):
    """See `IPackageUpload`."""

    # If this is a binary or mixed upload, we don't send *any* emails
    # provided it's not a rejection or a security upload:
    if (
        packageupload.from_build and
        packageupload.status != PackageUploadStatus.REJECTED and
        packageupload.pocket != PackagePublishingPocket.SECURITY):
        debug(logger, "Not sending email; upload is from a build.")
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
        changes_file_object)

    spr = packageupload.sourcepackagerelease

    if spr is None:
        # The sourcepackagerelease object that PackageUpload has fed us is
        # fake.
        notify_spr_less(
            None, changes_file_object.name, changes, summary_text,
            logger=logger)
        return

    bprs = packageupload.builds
    customfiles = packageupload.customfiles
    archive = packageupload.archive
    distroseries = packageupload.distroseries
    pocket = packageupload.pocket

    # "files" will contain a list of tuples of filename,component,section.
    # If files is empty, we don't need to send an email if this is not
    # a rejection.
    try:
        files = _buildUploadedFilesList(spr, bprs, customfiles, logger)
    except LanguagePackEncountered:
        # Don't send emails for language packs.
        return

    if not files and packageupload.status != PackageUploadStatus.REJECTED:
        return

    if packageupload.status == PackageUploadStatus.NEW:
        action = 'new'
    elif packageupload.status == PackageUploadStatus.UNAPPROVED:
        action = 'unapproved'
    else:
        action = 'accepted'

    summary = _buildSummary(spr, files, action)
    if summary_text:
        summary.append(summary_text)
    summarystring = "\n".join(summary)

    recipients = _getRecipients(
        packageupload.signing_key, archive, distroseries, changes, logger)

    # There can be no recipients if none of the emails are registered
    # in LP.
    if not recipients:
        debug(logger, "No recipients on email, not sending.")
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
            spr, bprs, customfiles, archive, distroseries, pocket,
            recipients, changes_lines, changes, summary_text, dry_run,
            changesfile_content, logger)
        return

    _sendSuccessNotification(
        spr, bprs, customfiles, archive, distroseries, pocket, recipients,
        announce_list, changes_lines, changes, summarystring, action,
        dry_run, changesfile_content, logger)


def assemble_body(spr, archive, distroseries, summary, changes, action):
    information = {
        'STATUS': get_status(action),
        'SUMMARY': summary,
        'DATE': 'Date: %s' % changes['Date'],
        'CHANGESFILE': ChangesFile.formatChangesComment(
            guess_encoding(changes.get('Changes'))),
        'DISTRO': distroseries.distribution.title,
        'ANNOUNCE': 'No announcement sent',
        'CHANGEDBY': '',
        'ORIGIN': '',
        'SIGNER': '',
        'SPR_URL': canonical_url(spr),
        'USERS_ADDRESS': config.launchpad.users_address,
        }
    changedby = guess_encoding(changes.get('Changed-By'))
    if changedby:
        information['CHANGEDBY'] = '\nChanged-By: %s' % changedby
    origin = changes.get('Origin')
    if origin:
        information['ORIGIN'] = '\nOrigin: %s' % origin
    if action == 'unapproved':
        information['SUMMARY'] += (
            "\nThis upload awaits approval by a distro manager\n")
    if distroseries.changeslist:
        information['ANNOUNCE'] = "Announcing to %s" % (
            distroseries.changeslist)
    if spr.package_upload is not None:
        if spr.package_upload.signing_key is not None:
            signer = spr.package_upload.signing_key.owner
            signer_signature = '%s <%s>' % (
                signer.displayname, signer.preferredemail.email)
            if signer_signature != changedby:
                information['SIGNER'] = '\nSigned-By: %s' % signer_signature
    # Add maintainer if present and different from changed-by.
    maintainer = guess_encoding(changes.get('Maintainer'))
    if maintainer and maintainer != changedby:
        information['MAINTAINER'] = '\nMaintainer: %s' % maintainer
    return get_template(archive, action) % information


def send_mail(spr, bprs, customfiles, archive, distroseries, pocket,
              summary_text, changes, recipients, dry_run, action,
              changesfile_content=None, from_addr=None, bcc=None,
              announce_list=None, logger=None):
    # Packageupload:
    # Summary_text: The body of the message.
    # Changes: A dictionary of the parsed changes file.
    # recipients: Who to send the mail to.
    # dry_run: Should we send the mail?
    # action: A string, documenting what sort of mail we are sending.
    # changesfile_content: A file-like object of the changes file.
    # from_addr: Which address to send the mail from.
    # bcc: Which addresses to BCC.
    # announce_list: Which list to announce the upload to.
    # logger: A logger object.
    attach_changes = not archive.is_ppa

    subject = calculate_subject(
        spr, bprs, customfiles, archive, distroseries, pocket, action)
    body = assemble_body(
        spr, archive, distroseries, summary_text, changes, action)

    _sendMail(
        spr, archive, recipients, subject, body, dry_run,
        changesfile_content=changesfile_content,
        attach_changes=attach_changes, from_addr=from_addr, bcc=bcc,
        logger=logger)


def _sendSuccessNotification(
    spr, bprs, customfiles, archive, distroseries, pocket, recipients,
    announce_list, changes_lines, changes, summarystring, action, dry_run,
    changesfile_content, logger):
    """Send a success email."""

    def do_send_mail(action=None):
        send_mail(spr, bprs, customfiles, archive, distroseries, pocket,
            summarystring, changes, recipients, dry_run, action,
            changesfile_content=changesfile_content, logger=logger)

    if action == 'new':
        # This is an unknown upload.
        do_send_mail(action=action)
        return

    # Unapproved uploads coming from an insecure policy only send
    # an acceptance message.
    if action == 'unapproved':
        # Only send an acceptance message.
        do_send_mail(action=action)
        return

    if archive.is_ppa:
        # PPA uploads receive an acceptance message.
        do_send_mail(action='accepted')
        return

    # Auto-approved uploads to backports skips the announcement,
    # they are usually processed with the sync policy.
    if pocket == PackagePublishingPocket.BACKPORTS:
        debug(logger, "Skipping announcement, it is a BACKPORT.")
        do_send_mail(action='accepted')
        return

    # Auto-approved binary-only uploads to security skip the
    # announcement, they are usually processed with the security policy.
    if pocket == PackagePublishingPocket.SECURITY and spr is not None:
        # We only send announcements if there is any source in the upload.
        debug(
            logger,
            "Skipping announcement, it is a binary upload to SECURITY.")
        do_send_mail(action='accepted')
        return

    # Fallback, all the rest coming from insecure, secure and sync
    # policies should send an acceptance and an announcement message.
    do_send_mail(action='accepted')

    # Don't send announcements for Debian auto sync uploads.
    if is_auto_sync_upload(spr, bprs, pocket, changes['Changed-By']):
        return

    if announce_list:
        from_addr = guess_encoding(changes['Changed-By'])

        send_mail(spr, bprs, customfiles, archive, distroseries, pocket,
            summarystring, changes, [str(announce_list)], dry_run,
            'announcement', changesfile_content=changesfile_content,
            from_addr=from_addr,
            bcc="%s_derivatives@packages.qa.debian.org" % spr.name,
            logger=logger)


def _sendRejectionNotification(
    spr, bprs, customfiles, archive, distroseries, pocket, recipients,
    changes_lines, changes, summary_text, dry_run, changesfile_content,
    logger):
    """Send a rejection email."""

    default_recipient = "%s <%s>" % (
        config.uploader.default_recipient_name,
        config.uploader.default_recipient_address)
    if not recipients:
        recipients = [default_recipient]

    debug(logger, "Sending rejection email.")
    send_mail(spr, bprs, customfiles, archive, distroseries, pocket,
        summary_text, changes, recipients, dry_run, 'rejected',
        changesfile_content=changesfile_content, logger=logger)


def _sendMail(
    spr, archive, to_addrs, subject, mail_text, dry_run, from_addr=None,
    bcc=None, changesfile_content=None, attach_changes=False, logger=None):
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

    # Include the 'X-Launchpad-PPA' header for PPA upload notfications
    # containing the PPA owner name.
    if archive.is_ppa:
        extra_headers['X-Launchpad-PPA'] = get_ppa_reference(archive)

    # Include a 'X-Launchpad-Component' header with the component and
    # the section of the source package uploaded in order to facilitate
    # filtering on the part of the email recipients.
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

    send_message(
        subject, from_addr, recipients, extra_headers, mail_text,
        dry_run=dry_run, attach_changes=attach_changes,
        changesfile_content=changesfile_content, logger=logger)


def send_message(subject, from_addr, recipients, extra_headers, mail_text,
                dry_run=None, attach_changes=None, changesfile_content=None,
                logger=None):
    if dry_run and logger is not None:
        logger.info("Would have sent a mail:")
        logger.info("  Subject: %s" % subject)
        logger.info("  Sender: %s" % from_addr)
        logger.info("  Recipients: %s" % recipients)
        logger.info("  Bcc: %s" % extra_headers['Bcc'])
        logger.info("  Body:")
        for line in mail_text.splitlines():
            logger.info(line)
    else:
        debug(logger, "Sent a mail:")
        debug(logger, "    Subject: %s" % subject)
        debug(logger, "    Recipients: %s" % recipients)
        debug(logger, "    Body:")
        for line in mail_text.splitlines():
            debug(logger, line)

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
        message.attach(MIMEText(mail_text.encode('utf-8'), 'plain', 'utf-8'))

        if attach_changes:
            # Add the original changesfile as an attachment.
            if changesfile_content is not None:
                changesfile_text = guess_encoding(changesfile_content)
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


def debug(logger, msg):
    """Shorthand debug notation for publish() methods."""
    if logger is not None:
        logger.debug(msg)


def _getRecipients(blamer, archive, distroseries, changes, logger):
    """Return a list of recipients for notification emails."""
    candidate_recipients = []
    debug(logger, "Building recipients list.")
    changer = _emailToPerson(changes['Changed-By'])

    if blamer:
        # This is a signed upload.
        candidate_recipients.append(blamer.owner)
    else:
        debug(logger,
            "Changes file is unsigned, adding changer as recipient")
        candidate_recipients.append(changer)

    if archive.is_ppa:
        # For PPAs, any person or team mentioned explicitly in the
        # ArchivePermissions as uploaders for the archive will also
        # get emailed.
        uploaders = [
            permission.person for permission in
                archive.getUploadersForComponent()]
        candidate_recipients.extend(uploaders)

    # If this is not a PPA, we also consider maintainer and changed-by.
    if blamer and not archive.is_ppa:
        maintainer = _emailToPerson(changes['Maintainer'])
        if (maintainer and maintainer != blamer.owner and
                maintainer.isUploader(distroseries.distribution)):
            debug(logger, "Adding maintainer to recipients")
            candidate_recipients.append(maintainer)

        if (changer and changer != blamer.owner and
                changer.isUploader(distroseries.distribution)):
            debug(logger, "Adding changed-by to recipients")
            candidate_recipients.append(changer)

    # Now filter list of recipients for persons only registered in
    # Launchpad to avoid spamming the innocent.
    recipients = []
    for person in candidate_recipients:
        if person is None or person.preferredemail is None:
            continue
        recipient = format_address(person.displayname,
            person.preferredemail.email)
        debug(logger, "Adding recipient: '%s'" % recipient)
        recipients.append(recipient)

    return recipients


def _buildUploadedFilesList(spr, builds, customfiles, logger):
    """Return a list of tuples of (filename, component, section).

    Component and section are only set where the file is a source upload.
    If an empty list is returned, it means there are no files.
    Raises LanguagePackRejection if a language pack is detected.
    No emails should be sent for language packs.
    """
    files = []
    # Bail out early if this is an upload for the translations
    # section.
    if spr.section.name == 'translations':
        debug(logger,
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
    for build in builds:
        for bpr in build.build.binarypackages:
            files.extend([
            (bpf.libraryfile.filename, '', '') for bpf in bpr.files])

    if customfiles:
        files.extend(
            [(file.libraryfilealias.filename, '', '')
            for file in customfiles])

    return files


def _buildSummary(spr, files, action):
    """Build a summary string based on the files present in the upload."""
    summary = []
    for filename, component, section in files:
        if action == 'new':
            summary.append("NEW: %s" % filename)
        else:
            summary.append(" OK: %s" % filename)
            if filename.endswith("dsc"):
                summary.append("     -> Component: %s Section: %s" % (
                    component, section))
    return summary


def _emailToPerson(fullemail):
    """Return an IPerson given an RFC2047 email address."""
    # The 2nd arg to s_f_m() doesn't matter as it won't fail since every-
    # thing will have already parsed at this point.
    (rfc822, rfc2047, name, email) = safe_fix_maintainer(
        fullemail, "email")
    return getUtility(IPersonSet).getByEmail(email)


def is_auto_sync_upload(spr, bprs, pocket, changed_by_email):
    katie = getUtility(ILaunchpadCelebrities).katie
    changed_by = _emailToPerson(changed_by_email)
    return (
        spr and not bprs and changed_by == katie and
        pocket != PackagePublishingPocket.SECURITY)


class LanguagePackEncountered(Exception):
    """Thrown when not wanting to email notifications for language packs."""
