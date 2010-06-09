# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


__metaclass__ = type

__all__ = [
    'SourcePackageRecipeBuildMailer',
    ]


from canonical.launchpad.webapp import canonical_url
from lp.services.mail.basemailer import BaseMailer, RecipientReason


class SourcePackageRecipeBuildMailer(BaseMailer):

    @classmethod
    def forStatus(cls, build):
        requester = build.requester
        recipients = {requester: RecipientReason.forBuildRequester(requester)}
        return cls(
            '%(status)s: %(recipe)s for %(distroseries)s',
            'build-request.txt', recipients, 'from_address', build)

    def __init__(self, subject, body_template, recipients, from_address,
                 build):
        BaseMailer.__init__(
            self, subject, body_template, recipients, from_address)
        self.build = build

    def _getTemplateParams(self, email):
        params = super(
            SourcePackageRecipeBuildMailer, self)._getTemplateParams(email)
        params.update({
            'status': str(self.build.buildstate),
            'distroseries': self.build.distroseries.name,
            'recipe': self.build.recipe.name,
            'recipe_owner': self.build.recipe.owner.name,
            'archive': self.build.archive.name,
            'build_url': canonical_url(self.build),
        })
        return params

    def _getFooter(self, params):
        return ('%(build_url)s\n'
                '%(reason)s\n' % params)
