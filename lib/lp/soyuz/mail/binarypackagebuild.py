# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BinaryPackageBuildMailer',
    ]

from collections import OrderedDict

from zope.component import getUtility

from lp.app.browser.tales import DurationFormatterAPI
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archivepublisher.utils import get_ppa_reference
from lp.buildmaster.enums import BuildStatus
from lp.services.config import config
from lp.services.mail.basemailer import (
    BaseMailer,
    RecipientReason,
    )
from lp.services.mail.helpers import get_contact_email_addresses
from lp.services.mail.mailwrapper import MailWrapper
from lp.services.mail.sendmail import format_address
from lp.services.webapp import canonical_url


class BinaryPackageBuildRecipientReason(RecipientReason):

    @classmethod
    def forCreator(cls, creator, recipient):
        header = cls.makeRationale("Creator", creator)
        reason = (
            "You are receiving this email because you created this version of "
            "this package.")
        return cls(creator, recipient, header, reason)

    @classmethod
    def forSigner(cls, signer, recipient):
        header = cls.makeRationale("Signer", signer)
        reason = (
            "You are receiving this email because you signed this package.")
        return cls(signer, recipient, header, reason)

    @classmethod
    def forBuilddAdmins(cls, buildd_admins, recipient):
        header = cls.makeRationale("Buildd-Admin", buildd_admins)
        # The team is always the same, so don't bother with %(lc_entity_is)s
        # here.
        reason = (
            "You are receiving this email because you are a buildd "
            "administrator.")
        return cls(buildd_admins, recipient, header, reason)

    @classmethod
    def forArchiveOwner(cls, owner, recipient):
        header = cls.makeRationale("Owner", owner)
        reason = (
            "You are receiving this email because %(lc_entity_is)s the owner "
            "of this archive.")
        return cls(owner, recipient, header, reason)

    def getReason(self):
        """See `RecipientReason`."""
        return MailWrapper(width=72).format(
            super(BinaryPackageBuildRecipientReason, self).getReason())


class BinaryPackageBuildMailer(BaseMailer):

    app = 'soyuz'

    @classmethod
    def forStatus(cls, build, extra_info=None):
        """Create a mailer for notifying about package build status.

        :param build: The relevant build.
        """
        # Circular import.
        from lp.registry.model.person import get_recipients

        recipients = OrderedDict()

        # Currently there are 7038 SPR published in edgy which the creators
        # have no preferredemail. They are the autosync ones (creator = katie,
        # 3583 packages) and the untouched sources since we have migrated from
        # DAK (the rest). We should not spam Debian maintainers.

        # Please note that both the package creator and the package uploader
        # will be notified of failures if:
        #     * the 'notify_owner' flag is set
        #     * the package build (failure) occurred in the original
        #       archive.
        creator = build.source_package_release.creator
        package_was_not_copied = (
            build.archive == build.source_package_release.upload_archive)

        if package_was_not_copied and config.builddmaster.notify_owner:
            if (build.archive.is_ppa and creator.inTeam(build.archive.owner)
                or not build.archive.is_ppa):
                # If this is a PPA, the package creator should only be
                # notified if they are the PPA owner or in the PPA team.
                # (see bug 375757)
                # Non-PPA notifications inform the creator regardless.
                for recipient in get_recipients(creator):
                    if recipient not in recipients:
                        reason = BinaryPackageBuildRecipientReason.forCreator(
                            creator, recipient)
                        recipients[recipient] = reason
            signer = build.source_package_release.signing_key_owner
            if signer:
                for recipient in get_recipients(signer):
                    if recipient not in recipients:
                        reason = BinaryPackageBuildRecipientReason.forSigner(
                            signer, recipient)
                        recipients[recipient] = reason

        if not build.archive.is_ppa:
            buildd_admins = getUtility(ILaunchpadCelebrities).buildd_admin
            for recipient in get_recipients(buildd_admins):
                if recipient not in recipients:
                    reason = BinaryPackageBuildRecipientReason.forBuilddAdmins(
                        buildd_admins, recipient)
                    recipients[recipient] = reason
        else:
            for recipient in get_recipients(build.archive.owner):
                if recipient not in recipients:
                    reason = BinaryPackageBuildRecipientReason.forArchiveOwner(
                        build.archive.owner, recipient)
                    recipients[recipient] = reason

        # XXX cprov 2006-08-02: pending security recipients for SECURITY
        # pocket build. We don't build SECURITY yet :(

        fromaddress = format_address(
            config.builddmaster.default_sender_name,
            config.builddmaster.default_sender_address)
        subject = "[Build #%d] %s" % (build.id, build.title)
        if build.archive.is_ppa:
            subject += " [%s]" % build.archive.reference
        return cls(
            subject, "build-notification.txt", recipients, fromaddress, build,
            extra_info=extra_info)

    def __init__(self, subject, template_name, recipients, from_address,
                 build, extra_info=None):
        super(BinaryPackageBuildMailer, self).__init__(
            subject, template_name, recipients, from_address,
            notification_type="package-build-status")
        self.build = build
        self.extra_info = extra_info

    def _getHeaders(self, email, recipient):
        """See `BaseMailer`."""
        headers = super(BinaryPackageBuildMailer, self)._getHeaders(
            email, recipient)
        build = self.build
        headers.update({
            "X-Launchpad-Archive": build.archive.reference,
            "X-Launchpad-Build-State": build.status.name,
            "X-Launchpad-Build-Component": build.current_component.name,
            "X-Launchpad-Build-Arch": build.distro_arch_series.architecturetag,
            # XXX cprov 2006-10-27: Temporary extra debug info about the
            # SPR.creator in context, to be used during the service
            # quarantine, notify_owner will be disabled to avoid *spamming*
            # Debian people.
            "X-Creator-Recipient": ",".join(get_contact_email_addresses(
                build.source_package_release.creator)),
            })
        # The deprecated PPA reference header is included for Ubuntu PPAs to
        # avoid breaking existing consumers.
        if (build.archive.is_ppa and
                build.archive.distribution.name == u'ubuntu'):
            headers["X-Launchpad-PPA"] = get_ppa_reference(build.archive)
        return headers

    def _getTemplateParams(self, email, recipient):
        params = super(BinaryPackageBuildMailer, self)._getTemplateParams(
            email, recipient)
        build = self.build
        extra_info = self.extra_info

        if build.archive.is_ppa:
            source_url = "not available"
        else:
            source_url = canonical_url(build.distributionsourcepackagerelease)

        # XXX cprov 2006-08-02: find out a way to glue parameters reported
        # with the state in the build workflow, maybe by having an
        # IBuild.statusReport property, which could also be used in the
        # respective page template.
        if build.status in (BuildStatus.NEEDSBUILD, BuildStatus.SUPERSEDED):
            # untouched builds
            buildduration = "not available"
            buildlog_url = "not available"
            builder_url = "not available"
        elif build.status == BuildStatus.UPLOADING:
            buildduration = "uploading"
            buildlog_url = "see builder page"
            builder_url = "not available"
        elif build.status == BuildStatus.BUILDING:
            # build in process
            buildduration = "not finished"
            buildlog_url = "see builder page"
            builder_url = canonical_url(build.buildqueue_record.builder)
        else:
            # completed states (success and failure)
            buildduration = DurationFormatterAPI(
                build.duration).approximateduration()
            buildlog_url = build.log_url
            builder_url = canonical_url(build.builder)

        if build.status == BuildStatus.FAILEDTOUPLOAD:
            assert extra_info is not None, (
                "Extra information is required for FAILEDTOUPLOAD "
                "notifications.")
            extra_info = "Upload log:\n%s" % extra_info
        else:
            extra_info = ""

        params.update({
            "source_name": build.source_package_release.name,
            "source_version": build.source_package_release.version,
            "architecturetag": build.distro_arch_series.architecturetag,
            "build_state": build.status.title,
            "build_duration": buildduration,
            "buildlog_url": buildlog_url,
            "builder_url": builder_url,
            "build_title": build.title,
            "build_url": canonical_url(build),
            "source_url": source_url,
            "extra_info": extra_info,
            "archive_tag": build.archive.reference,
            "component_tag": build.current_component.name,
            })
        return params

    def _getFooter(self, email, recipient, params):
        """See `BaseMailer`."""
        return ("%(build_title)s\n"
                "%(build_url)s\n\n"
                "%(reason)s\n" % params)
