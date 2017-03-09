# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create a bot account."""

from zope.component import getUtility

from lp.registry.interfaces.person import (
    IPersonSet,
    PersonCreationRationale,
)
from lp.registry.interfaces.ssh import ISSHKeySet
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )
from lp.services.webapp import canonical_url


class CreateBotAccountScript(LaunchpadScript):

    description = "Create a bot account."
    output = None

    def add_my_options(self):
        self.parser.add_option(
            '--name', metavar='NAME', action='store',
            type='string', dest='name', default=None,
            help='Username for the bot')
        self.parser.add_option(
            '--openid', metavar='OPENID_SUFFIX', action='store',
            type='string', dest='openid', default=None,
            help='OpenID identifier. Just the suffix, not the full URL')
        self.parser.add_option(
            '--email', metavar='ADDR', action='store',
            type='string', dest='email', default=None,
            help='Email address. Defaults to webops+username@canonical.com')
        self.parser.add_option(
            '--sshkey', metavar='TXT', action='store',
            type='string', dest='sshkey', default=None,
            help='SSH public key. Defaults to no ssh key.')
        self.parser.add_option(
            '--teams', metavar='TEAMS', action='store',
            type='string', dest='teams',
            default='canonical-is-devopsolution-bots',
            help='Add bot to this comma separated list of teams')

    def main(self):
        username = unicode(self.options.name)
        if not username:
            raise LaunchpadScriptFailure('--name is a required option')

        openid_suffix = unicode(self.options.openid)
        if not openid_suffix:
            raise LaunchpadScriptFailure('--openid is a required option')
        if '/' in openid_suffix:
            raise LaunchpadScriptFailure(
                '{} is not a valid openid suffix'.format(openid_suffix))

        displayname = u'{} McBotface'.format(username)

        if self.options.email:
            emailaddress = unicode(self.options.email)
        else:
            emailaddress = u'webops+{}@canonical.com'.format(username)

        if self.options.teams:
            teamnames = [unicode(t.strip())
                         for t in self.options.teams.split(',')
                         if t.strip()]
        else:
            teamnames = []

        sshkey_text = unicode(self.options.sshkey)  # Optional

        person_set = getUtility(IPersonSet)

        # Create the IPerson
        person, _ = person_set.getOrCreateByOpenIDIdentifier(
            unicode(openid_suffix),
            emailaddress,
            displayname,
            # If we want a specific rationale, we should also update
            # existing bot accounts.
            PersonCreationRationale.OWNER_CREATED_LAUNCHPAD,
            comment="when the create-bot-account launchpad script was run")

        person.name = username
        person.selfgenerated_bugnotifications = True
        person.expanded_notification_footers = True
        person.description = 'Canonical IS created bot'
        person.hide_email_addresses = True

        # Validate the email address
        person.validateAndEnsurePreferredEmail(person.preferredemail)

        # Add team memberships
        for teamname in teamnames:
            team = person_set.getByName(teamname)
            if team is None or not team.is_team:
                raise LaunchpadScriptFailure(
                    '{} is not a team'.format(teamname))
            team.addMember(person, person)

        # Add ssh key
        sshkey_set = getUtility(ISSHKeySet)
        if sshkey_text and not sshkey_set.getByPersonAndKeyText(person,
                                                                sshkey_text):
            sshkey_set.new(person, sshkey_text, send_notification=False)

        self.logger.info('Created or updated {}'.format(canonical_url(person)))
        self.txn.commit()
