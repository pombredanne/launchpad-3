# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LiveFSBuildMailer',
    ]

from lp.app.browser.tales import DurationFormatterAPI
from lp.services.config import config
from lp.services.mail.basemailer import (
    BaseMailer,
    RecipientReason,
    )
from lp.services.webapp import canonical_url


class LiveFSBuildMailer(BaseMailer):

    app = 'soyuz'

    @classmethod
    def forStatus(cls, build):
        """Create a mailer for notifying about live filesystem build status.

        :param build: The relevant build.
        """
        requester = build.requester
        recipients = {requester: RecipientReason.forBuildRequester(requester)}
        return cls(
            "[LiveFS build #%(build_id)d] %(build_title)s",
            "livefsbuild-notification.txt", recipients,
            config.canonical.noreply_from_address, build)

    def __init__(self, subject, template_name, recipients, from_address,
                 build):
        super(LiveFSBuildMailer, self).__init__(
            subject, template_name, recipients, from_address,
            notification_type="livefs-build-status")
        self.build = build

    def _getHeaders(self, email, recipient):
        """See `BaseMailer`."""
        headers = super(LiveFSBuildMailer, self)._getHeaders(email, recipient)
        headers["X-Launchpad-Build-State"] = self.build.status.name
        return headers

    def _getTemplateParams(self, email, recipient):
        """See `BaseMailer`."""
        build = self.build
        params = super(LiveFSBuildMailer, self)._getTemplateParams(
            email, recipient)
        params.update({
            "archive_tag": build.archive.reference,
            "build_id": build.id,
            "build_title": build.title,
            "livefs_name": build.livefs.name,
            "version": build.version,
            "distroseries": build.livefs.distro_series,
            "architecturetag": build.distro_arch_series.architecturetag,
            "pocket": build.pocket.name,
            "build_state": build.status.title,
            "build_duration": "",
            "log_url": "",
            "upload_log_url": "",
            "builder_url": "",
            "build_url": canonical_url(self.build),
            })
        if build.duration is not None:
            duration_formatter = DurationFormatterAPI(build.duration)
            params["build_duration"] = duration_formatter.approximateduration()
        if build.log is not None:
            params["log_url"] = build.log_url
        if build.upload_log is not None:
            params["upload_log_url"] = build.upload_log_url
        if build.builder is not None:
            params["builder_url"] = canonical_url(build.builder)
        return params

    def _getFooter(self, email, recipient, params):
        """See `BaseMailer`."""
        return ("%(build_url)s\n"
                "%(reason)s\n" % params)
