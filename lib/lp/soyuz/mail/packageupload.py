# Copyright 2011-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageUploadMailer',
    ]

from collections import OrderedDict
import os.path

from zope.component import getUtility
from zope.security.proxy import isinstance as zope_isinstance

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archivepublisher.utils import get_ppa_reference
from lp.archiveuploader.changesfile import ChangesFile
from lp.archiveuploader.utils import (
    parse_maintainer_bytes,
    ParseMaintError,
    rfc822_encode_address,
    )
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.config import config
from lp.services.encoding import guess as guess_encoding
from lp.services.mail.basemailer import (
    BaseMailer,
    RecipientReason,
    )
from lp.services.mail.mailwrapper import MailWrapper
from lp.services.mail.notificationrecipientset import StubPerson
from lp.services.mail.sendmail import (
    format_address,
    format_address_for_person,
    )
from lp.services.webapp import canonical_url
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet


class PackageUploadRecipientReason(RecipientReason):

    @classmethod
    def forRequester(cls, requester, recipient):
        header = cls.makeRationale("Requester", requester)
        # This is a little vague - copies may end up here too - but it's
        # close enough.
        reason = "You are receiving this email because you made this upload."
        return cls(requester, recipient, header, reason)

    @classmethod
    def forMaintainer(cls, maintainer, recipient):
        header = cls.makeRationale("Maintainer", maintainer)
        reason = (
            "You are receiving this email because %(lc_entity_is)s listed as "
            "this package's maintainer.")
        return cls(maintainer, recipient, header, reason)

    @classmethod
    def forChangedBy(cls, changed_by, recipient):
        header = cls.makeRationale("Changed-By", changed_by)
        reason = (
            "You are receiving this email because %(lc_entity_is)s the most "
            "recent person listed in this package's changelog.")
        return cls(changed_by, recipient, header, reason)

    @classmethod
    def forPPAUploader(cls, uploader, recipient):
        header = cls.makeRationale("PPA Uploader", uploader)
        reason = (
            "You are receiving this email because %(lc_entity_has)s upload "
            "permissions to this PPA.")
        return cls(uploader, recipient, header, reason)

    @classmethod
    def forAnnouncement(cls, recipient):
        return cls(recipient, recipient, "Announcement", "")

    def _getTemplateValues(self):
        template_values = super(
            PackageUploadRecipientReason, self)._getTemplateValues()
        template_values["lc_entity_has"] = "you have"
        if self.recipient != self.subscriber or self.subscriber.is_team:
            template_values["lc_entity_has"] = (
                "your team %s has" % self.subscriber.displayname)
        return template_values

    def getReason(self):
        """See `RecipientReason`."""
        return MailWrapper(width=72).format(
            super(PackageUploadRecipientReason, self).getReason())


def debug(logger, msg, *args, **kwargs):
    """Shorthand debug notation."""
    if logger is not None:
        logger.debug(msg, *args, **kwargs)


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


def add_recipient(recipients, person, reason_factory, logger=None):
    # Circular import.
    from lp.registry.model.person import get_recipients

    if person is None:
        return
    for recipient in get_recipients(person):
        if recipient not in recipients:
            debug(
                logger, "Adding recipient: '%s'" % format_address_for_person(
                    recipient))
            reason = reason_factory(person, recipient)
            recipients[recipient] = reason


def fetch_information(spr, bprs, changes, previous_version=None):
    changelog = date = changedby = maintainer = None

    if changes:
        changelog = ChangesFile.formatChangesComment(
            sanitize_string(changes.get('Changes')))
        date = changes.get('Date')
        try:
            changedby = parse_maintainer_bytes(
                changes.get('Changed-By'), 'Changed-By')
        except ParseMaintError:
            pass
        try:
            maintainer = parse_maintainer_bytes(
                changes.get('Maintainer'), 'Maintainer')
        except ParseMaintError:
            pass
    elif spr or bprs:
        if not spr and bprs:
            spr = bprs[0].build.source_package_release
        changelog = spr.aggregate_changelog(previous_version)
        date = spr.dateuploaded
        if spr.creator and spr.creator.preferredemail:
            changedby = (
                spr.creator.displayname, spr.creator.preferredemail.email)
        if spr.maintainer and spr.maintainer.preferredemail:
            maintainer = (
                spr.maintainer.displayname,
                spr.maintainer.preferredemail.email)

    return {
        'changelog': changelog,
        'date': date,
        'changedby': changedby,
        'maintainer': maintainer,
        }


def addr_to_person(addr):
    """Return an `IPerson` given a name and email address.

    :param addr: (name, email) tuple. The name is ignored.
    :return: `IPerson` with the given email address.  None if there
        isn't one, or if `addr` is None.
    """
    if addr is None:
        return None
    return getUtility(IPersonSet).getByEmail(addr[1])


def is_valid_uploader(person, distribution):
    """Is `person` an uploader for `distribution`?

    A `None` person is not an uploader.
    """
    if person is None:
        return None
    else:
        return not getUtility(IArchivePermissionSet).componentsForUploader(
            distribution.main_archive, person).is_empty()


def is_auto_sync_upload(spr, bprs, pocket, changed_by):
    """Return True if this is a (Debian) auto sync upload.

    Sync uploads are source-only, unsigned and not targeted to
    the security pocket. The Changed-By field is also the Katie
    user (archive@ubuntu.com).
    """
    changed_by = addr_to_person(changed_by)
    return (
        spr and
        not bprs and
        changed_by == getUtility(ILaunchpadCelebrities).katie and
        pocket != PackagePublishingPocket.SECURITY)


ACTION_DESCRIPTIONS = {
    'new': 'New',
    'unapproved': 'Waiting for approval',
    'rejected': 'Rejected',
    'accepted': 'Accepted',
    'announcement': 'Accepted',
    }


def calculate_subject(spr, bprs, customfiles, archive, distroseries,
                      pocket, action, changesfile_object=None):
    """Return the email subject for the notification."""
    names = set()
    version = '-'
    if spr:
        names.add(spr.name)
        version = spr.version
    elif bprs:
        names.add(bprs[0].build.source_package_release.name)
        version = bprs[0].build.source_package_release.version
    for custom in customfiles:
        names.add(custom.libraryfilealias.filename)
    if names:
        archive_and_suite = '%s/%s' % (
            archive.reference, distroseries.getSuite(pocket))
        name_and_version = '%s %s' % (', '.join(names), version)
    else:
        if changesfile_object is None:
            return None
        # The suite may not be meaningful if we have no
        # spr/bprs/customfiles, since this must be a very early rejection.
        # Don't introduce confusion by including it.
        archive_and_suite = archive.reference
        name_and_version = os.path.basename(changesfile_object.name)
    subject = '[%s] %s (%s)' % (
        archive_and_suite, name_and_version, ACTION_DESCRIPTIONS[action])
    return subject


def build_uploaded_files_list(spr, builds, customfiles, logger):
    """Return a list of tuples of (filename, component, section).

    Component and section are only set where the file is a source upload.
    If an empty list is returned, it means there are no files.
    """
    if spr:
        for sprfile in spr.files:
            yield (
                sprfile.libraryfile.filename, spr.component.name,
                spr.section.name)

    # Component and section don't get set for builds and custom, since
    # this information is only used in the summary string for source
    # uploads.
    for build in builds:
        for bpr in build.build.binarypackages:
            for bpf in bpr.files:
                yield bpf.libraryfile.filename, '', ''

    if customfiles:
        for customfile in customfiles:
            yield customfile.libraryfilealias.filename, '', ''


def build_summary(spr, files, action):
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


class PackageUploadMailer(BaseMailer):

    app = 'soyuz'

    @classmethod
    def getRecipientsForAction(cls, action, info, blamee, spr, bprs, archive,
                               distroseries, pocket, announce_from_person=None,
                               logger=None):
        # If this is a binary or mixed upload, we don't send *any* emails
        # provided it's not a rejection or a security upload:
        if (
            bprs and action != 'rejected' and
            pocket != PackagePublishingPocket.SECURITY):
            debug(logger, "Not sending email; upload is from a build.")
            return {}, ''

        if spr and spr.source_package_recipe_build and action == 'accepted':
            debug(logger, "Not sending email; upload is from a recipe.")
            return {}, ''

        if spr and spr.section.name == 'translations':
            debug(
                logger,
                "Skipping acceptance and announcement for language packs.")
            return {}, ''

        debug(logger, "Building recipients list.")
        recipients = OrderedDict()

        add_recipient(
            recipients, blamee, PackageUploadRecipientReason.forRequester,
            logger=logger)

        changer = addr_to_person(info['changedby'])
        maintainer = addr_to_person(info['maintainer'])

        if blamee is None and not archive.is_copy:
            debug(
                logger,
                "Changes file is unsigned; adding changer as recipient.")
            add_recipient(
                recipients, changer, PackageUploadRecipientReason.forChangedBy,
                logger=logger)

        if archive.is_ppa:
            # For PPAs, any person or team mentioned explicitly in the
            # ArchivePermissions as uploaders for the archive will also get
            # emailed.
            for permission in archive.getUploadersForComponent():
                add_recipient(
                    recipients, permission.person,
                    PackageUploadRecipientReason.forPPAUploader, logger=logger)
        elif archive.is_copy:
            # For copy archives, notifying anyone else will probably only
            # confuse them.
            pass
        else:
            # If this is not a PPA, we also consider maintainer and changed-by.
            if blamee is not None:
                if is_valid_uploader(maintainer, distroseries.distribution):
                    debug(logger, "Adding maintainer to recipients")
                    add_recipient(
                        recipients, maintainer,
                        PackageUploadRecipientReason.forMaintainer,
                        logger=logger)

                if is_valid_uploader(changer, distroseries.distribution):
                    debug(logger, "Adding changed-by to recipients")
                    add_recipient(
                        recipients, changer,
                        PackageUploadRecipientReason.forChangedBy,
                        logger=logger)

        if announce_from_person is not None:
            announce_from_addr = (
                announce_from_person.displayname,
                announce_from_person.preferredemail.email)
        else:
            announce_from_addr = info['changedby']

        # If we're sending an acceptance notification for a non-PPA upload,
        # announce if possible. Avoid announcing backports, binary-only
        # security uploads, or autosync uploads.
        if (action == 'accepted' and distroseries.changeslist
                and not archive.is_ppa
                and pocket != PackagePublishingPocket.BACKPORTS
                and not (
                    pocket == PackagePublishingPocket.SECURITY and spr is None)
                and not is_auto_sync_upload(
                    spr, bprs, pocket, announce_from_addr)):
            recipient = StubPerson(distroseries.changeslist)
            recipients[recipient] = (
                PackageUploadRecipientReason.forAnnouncement(recipient))

        if announce_from_addr is not None:
            announce_from_address = format_address(*announce_from_addr)
        else:
            announce_from_address = None
        return recipients, announce_from_address

    @classmethod
    def forAction(cls, action, blamee, spr, bprs, customfiles, archive,
                  distroseries, pocket, changes=None, changesfile_object=None,
                  announce_from_person=None, previous_version=None,
                  logger=None, **kwargs):
        info = fetch_information(
            spr, bprs, changes, previous_version=previous_version)
        recipients, announce_from_address = cls.getRecipientsForAction(
            action, info, blamee, spr, bprs, archive, distroseries, pocket,
            announce_from_person=announce_from_person, logger=logger)
        subject = calculate_subject(
            spr, bprs, customfiles, archive, distroseries, pocket, action,
            changesfile_object=changesfile_object)
        if subject is None:
            # We don't even have enough information to build a minimal
            # subject, so do nothing.
            recipients = {}
        template_name = "upload-"
        if action in ("new", "accepted", "announcement"):
            template_name += action
        elif action == "unapproved":
            template_name += "accepted"
        elif action == "rejected":
            template_name += "rejection"
        if archive.is_ppa:
            template_name = "ppa-%s" % template_name
        template_name += ".txt"
        from_address = format_address(
            config.uploader.default_sender_name,
            config.uploader.default_sender_address)
        return cls(
            subject, template_name, recipients, from_address, action, info,
            blamee, spr, bprs, customfiles, archive, distroseries, pocket,
            changes=changes, announce_from_address=announce_from_address,
            logger=logger, **kwargs)

    def __init__(self, subject, template_name, recipients, from_address,
                 action, info, blamee, spr, bprs, customfiles, archive,
                 distroseries, pocket, summary_text=None, changes=None,
                 changesfile_content=None, dry_run=False,
                 announce_from_address=None, previous_version=None,
                 logger=None):
        super(PackageUploadMailer, self).__init__(
            subject, template_name, recipients, from_address,
            notification_type="package-upload")
        self.action = action
        self.info = info
        self.blamee = blamee
        self.spr = spr
        self.bprs = bprs
        self.customfiles = customfiles
        self.archive = archive
        self.distroseries = distroseries
        self.pocket = pocket
        self.changes = changes
        self.changesfile_content = changesfile_content
        self.dry_run = dry_run
        self.logger = logger
        self.announce_from_address = announce_from_address
        self.previous_version = previous_version

        if action == 'rejected':
            self.summarystring = summary_text
        else:
            files = build_uploaded_files_list(spr, bprs, customfiles, logger)
            summary = build_summary(spr, files, action)
            if summary_text:
                summary.append(summary_text)
            self.summarystring = "\n".join(summary)

    def _getFromAddress(self, email, recipient):
        """See `BaseMailer`."""
        if (zope_isinstance(recipient, StubPerson) and
                self.announce_from_address is not None):
            return self.announce_from_address
        else:
            return super(PackageUploadMailer, self)._getFromAddress(
                email, recipient)

    def _getHeaders(self, email, recipient):
        """See `BaseMailer`."""
        headers = super(PackageUploadMailer, self)._getHeaders(
            email, recipient)
        headers['X-Katie'] = 'Launchpad actually'
        headers['X-Launchpad-Archive'] = self.archive.reference

        # The deprecated PPA reference header is included for Ubuntu PPAs to
        # avoid breaking existing consumers.
        if self.archive.is_ppa and self.archive.distribution.name == u'ubuntu':
            headers['X-Launchpad-PPA'] = get_ppa_reference(self.archive)

        # Include a 'X-Launchpad-Component' header with the component and
        # the section of the source package uploaded in order to facilitate
        # filtering on the part of the email recipients.
        if self.spr:
            headers['X-Launchpad-Component'] = 'component=%s, section=%s' % (
                self.spr.component.name, self.spr.section.name)

        # All emails from here have a Bcc to the default recipient.
        bcc_text = format_address(
            config.uploader.default_recipient_name,
            config.uploader.default_recipient_address)
        if zope_isinstance(recipient, StubPerson):
            name = None
            if self.spr:
                name = self.spr.name
            elif self.bprs:
                name = self.bprs[0].build.source_package_release.name
            if name:
                distribution = self.distroseries.distribution
                email_base = distribution.package_derivatives_email
                if email_base:
                    bcc_text += ", " + email_base.format(package_name=name)
        headers['Bcc'] = bcc_text

        return headers

    def _addAttachments(self, ctrl, email):
        """See `BaseMailer`."""
        if not self.archive.is_ppa:
            if self.changesfile_content is not None:
                changesfile_text = sanitize_string(self.changesfile_content)
            else:
                changesfile_text = "Sorry, changesfile not available."
            ctrl.addAttachment(
                changesfile_text, content_type='text/plain',
                filename='changesfile', charset='utf-8')

    def _getTemplateName(self, email, recipient):
        """See `BaseMailer`."""
        if zope_isinstance(recipient, StubPerson):
            return "upload-announcement.txt"
        else:
            return self._template_name

    def _getTemplateParams(self, email, recipient):
        """See `BaseMailer`."""
        params = super(PackageUploadMailer, self)._getTemplateParams(
            email, recipient)
        params.update({
            'STATUS': ACTION_DESCRIPTIONS[self.action],
            'SUMMARY': self.summarystring,
            'DATE': '',
            'CHANGESFILE': '',
            'DISTRO': self.distroseries.distribution.title,
            'ANNOUNCE': 'No announcement sent',
            'CHANGEDBY': '',
            'MAINTAINER': '',
            'ORIGIN': '',
            'SIGNER': '',
            'SPR_URL': '',
            'ARCHIVE_URL': canonical_url(self.archive),
            'USERS_ADDRESS': config.launchpad.users_address,
            })
        changes = self.changes
        if changes is None:
            changes = {}

        if self.info['date'] is not None:
            params['DATE'] = 'Date: %s' % self.info['date']
        if self.info['changelog'] is not None:
            params['CHANGESFILE'] = self.info['changelog']
        if self.spr:
            params['SPR_URL'] = canonical_url(
                self.distroseries.distribution.getSourcePackageRelease(
                    self.spr))

        # Some syncs (e.g. from Debian) will involve packages whose
        # changed-by person was auto-created in LP and hence does not have a
        # preferred email address set.  We'll get a None here.
        changedby_person = addr_to_person(self.info['changedby'])
        if self.info['changedby']:
            params['CHANGEDBY'] = '\nChanged-By: %s' % rfc822_encode_address(
                *self.info['changedby'])
        if (self.blamee is not None and self.blamee != changedby_person
                and self.blamee.preferredemail):
            params['SIGNER'] = '\nSigned-By: %s' % rfc822_encode_address(
                self.blamee.displayname, self.blamee.preferredemail.email)
        if (self.info['maintainer']
                and self.info['maintainer'] != self.info['changedby']):
            params['MAINTAINER'] = '\nMaintainer: %s' % rfc822_encode_address(
                *self.info['maintainer'])

        origin = changes.get('Origin')
        if origin:
            params['ORIGIN'] = '\nOrigin: %s' % origin
        if self.action == 'unapproved':
            params['SUMMARY'] += (
                "\nThis upload awaits approval by a distro manager\n")
        if self.distroseries.changeslist:
            params['ANNOUNCE'] = "Announcing to %s" % (
                self.distroseries.changeslist)

        return params

    def _getFooter(self, email, recipient, params):
        """See `BaseMailer`."""
        if zope_isinstance(recipient, StubPerson):
            return None
        else:
            footer_lines = []
            if self.archive.is_ppa:
                footer_lines.append("%(ARCHIVE_URL)s\n")
            footer_lines.append("%(reason)s\n")
            return "".join(footer_lines) % params

    def generateEmail(self, email, recipient, force_no_attachments=False):
        """See `BaseMailer`."""
        ctrl = super(PackageUploadMailer, self).generateEmail(
            email, recipient, force_no_attachments=force_no_attachments)
        if self.dry_run:
            debug(self.logger, "Would have sent a mail:")
        else:
            debug(self.logger, "Sent a mail:")
        debug(self.logger, "  Subject: %s" % ctrl.subject)
        debug(self.logger, "  Sender: %s" % ctrl.from_addr)
        debug(self.logger, "  Recipients: %s" % ", ".join(ctrl.to_addrs))
        if 'Bcc' in ctrl.headers:
            debug(self.logger, "  Bcc: %s" % ctrl.headers['Bcc'])
        debug(self.logger, "  Body:")
        for line in ctrl.body.splitlines():
            if isinstance(line, bytes):
                line = line.decode('utf-8', 'replace')
            debug(self.logger, line)
        return ctrl

    def sendOne(self, email, recipient):
        """See `BaseMailer`."""
        if self.dry_run:
            # Just generate the email for the sake of debugging output.
            self.generateEmail(email, recipient)
        else:
            super(PackageUploadMailer, self).sendOne(email, recipient)
