# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create a bot account."""

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

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
            '-u', '--username', metavar='NAME', action='store',
            type='string', dest='username', default='',
            help='Username for the bot')
        self.parser.add_option(
            '--openid', metavar='SUFFIX', action='store',
            type='string', dest='openid', default='',
            help=('OpenID identifier suffix. Normally unnecessary because '
                  'SSO account creation handles it'))
        self.parser.add_option(
            '-e', '--email', metavar='ADDR', action='store',
            type='string', dest='email', default='',
            help='Email address. Defaults to webops+username@canonical.com')
        self.parser.add_option(
            '-k', '--sshkey', metavar='TXT', action='store',
            type='string', dest='sshkey', default='',
            help='SSH public key. Defaults to no ssh key.')
        self.parser.add_option(
            '-t', '--teams', metavar='TEAMS', action='store',
            type='string', dest='teams',
            default='canonical-is-devopsolution-bots',
            help='Add bot to this comma separated list of teams')

    def main(self):
        username = unicode(self.options.username)
        if not username:
            raise LaunchpadScriptFailure('--username is required')
        openid_suffix = unicode(self.options.openid)
        if '/' in openid_suffix:
            raise LaunchpadScriptFailure(
                'Invalid OpenID suffix {}'.format(openid_suffix))

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

        if openid_suffix and person_set.getByName(username) is None:
            # Normally the SSO has already called this method.
            # This codepath is really only used for testing.
            person_set.createPlaceholderPerson(openid_suffix, username)

        person = person_set.getByName(username)
        if person is None:
            raise LaunchpadScriptFailure(
                'Account {} does not exist'.format(username))
        if person.account is None:
            raise LaunchpadScriptFailure(
                'Person {} has no Account'.format(username))
        if person.account.openid_identifiers.count() != 1:
            raise LaunchpadScriptFailure(
                'Account {} has invalid OpenID identifiers'.format(username))
        openid_identifier = person.account.openid_identifiers.one()

        # Create the IPerson
        person, _ = person_set.getOrCreateByOpenIDIdentifier(
            openid_identifier.identifier,
            emailaddress,
            displayname,
            PersonCreationRationale.BOT,  # Ignored, reset below
            comment="when the create-bot-account launchpad script was run")

        # person.name = username
        person.selfgenerated_bugnotifications = True
        person.expanded_notification_footers = True
        person.description = 'Canonical IS created bot'
        person.hide_email_addresses = True
        removeSecurityProxy(person).creation_rationale = (
            PersonCreationRationale.BOT)

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
        if sshkey_text and (
                sshkey_set.getByPersonAndKeyText(person,
                                                 sshkey_text).count() == 0):
            sshkey_set.new(person, sshkey_text, send_notification=False)

        self.logger.info('Created or updated {}'.format(canonical_url(person)))
        self.txn.commit()
