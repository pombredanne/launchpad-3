#!/usr/bin/python
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

from datetime import (
    datetime,
    timedelta,
    )
import filecmp
import os
import tempfile

import pytz
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp import canonical_url
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.htaccess import (
    htpasswd_credentials_for_archive,
    write_htaccess,
    write_htpasswd,
    )
from lp.registry.model.teammembership import TeamParticipation
from lp.services.mail.mailwrapper import MailWrapper
from lp.services.mail.sendmail import (
    format_address,
    simple_sendmail,
    )
from lp.services.scripts.base import LaunchpadCronScript
from lp.services.scripts.interfaces.scriptactivity import IScriptActivitySet
from lp.soyuz.enums import (
    ArchiveStatus,
    ArchiveSubscriberStatus,
    )
from lp.soyuz.model.archiveauthtoken import ArchiveAuthToken
from lp.soyuz.model.archivesubscriber import ArchiveSubscriber

# These PPAs should never have their htaccess/pwd files touched.
BLACKLISTED_PPAS = {
    'ubuntuone': ['ppa'],
    }


class HtaccessTokenGenerator(LaunchpadCronScript):
    """Helper class for generating .htaccess files for private PPAs."""
    blacklist = BLACKLISTED_PPAS

    def add_my_options(self):
        """Add script command line options."""
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", default=False,
            help="If set, no files are changed and no tokens are "
                 "deactivated.")
        self.parser.add_option(
            "-d", "--no-deactivation", action="store_true",
            dest="no_deactivation", default=False,
            help="If set, tokens are not deactivated.")

    def ensureHtaccess(self, ppa):
        """Generate a .htaccess for `ppa`."""
        if self.options.dryrun:
            return

        # The publisher Config object does not have an
        # interface, so we need to remove the security wrapper.
        pub_config = getPubConfig(ppa)
        htaccess_filename = os.path.join(pub_config.htaccessroot, ".htaccess")
        if not os.path.exists(htaccess_filename):
            # It's not there, so create it.
            if not os.path.exists(pub_config.htaccessroot):
                os.makedirs(pub_config.htaccessroot)
            write_htaccess(htaccess_filename, pub_config.htaccessroot)
            self.logger.debug("Created .htaccess for %s" % ppa.displayname)

    def generateHtpasswd(self, ppa, tokens):
        """Generate a htpasswd file for `ppa`s `tokens`.

        :param ppa: The context PPA (an `IArchive`).
        :param tokens: A iterable containing `IArchiveAuthToken`s.
        :return: The filename of the htpasswd file that was generated.
        """
        # Create a temporary file that will be a new .htpasswd.
        pub_config = getPubConfig(ppa)
        fd, temp_filename = tempfile.mkstemp(dir=pub_config.htaccessroot)
        os.close(fd)

        write_htpasswd(
            temp_filename, htpasswd_credentials_for_archive(ppa, tokens))

        return temp_filename

    def replaceUpdatedHtpasswd(self, ppa, temp_htpasswd_file):
        """Compare the new and the old htpasswd and replace if changed.

        :return: True if the file was replaced.
        """
        if self.options.dryrun:
            return False

        # The publisher Config object does not have an
        # interface, so we need to remove the security wrapper.
        pub_config = getPubConfig(ppa)
        htpasswd_filename = os.path.join(pub_config.htaccessroot, ".htpasswd")

        if (not os.path.isfile(htpasswd_filename) or
            not filecmp.cmp(htpasswd_filename, temp_htpasswd_file)):
            # Atomically replace the old file or create a new file.
            os.rename(temp_htpasswd_file, htpasswd_filename)
            self.logger.debug("Replaced htpasswd for %s" % ppa.displayname)
            return True

        return False

    def sendCancellationEmail(self, token):
        """Send an email to the person whose subscription was cancelled."""
        send_to_person = token.person
        ppa_name = token.archive.displayname
        ppa_owner_url = canonical_url(token.archive.owner)
        subject = "PPA access cancelled for %s" % ppa_name
        template = get_email_template("ppa-subscription-cancelled.txt")

        assert not send_to_person.isTeam(), (
            "Token.person is a team, it should always be individuals.")

        if send_to_person.preferredemail is None:
            # The person has no preferred email set, so we don't
            # email them.
            return

        to_address = [send_to_person.preferredemail.email]
        replacements = {
            'recipient_name': send_to_person.displayname,
            'ppa_name': ppa_name,
            'ppa_owner_url': ppa_owner_url,
            }
        body = MailWrapper(72).format(
            template % replacements, force_wrap=True)

        from_address = format_address(
            ppa_name,
            config.canonical.noreply_from_address)

        headers = {
            'Sender': config.canonical.bounce_address,
            }

        simple_sendmail(from_address, to_address, subject, body, headers)

    def deactivateTokens(self, send_email=False):
        """Deactivate tokens as necessary.

        If a subscriber no longer has an active token for the PPA, we
        deactivate it.

        :param send_email: Whether to send a cancellation email to the owner
            of the token.  This defaults to False to speed up the test
            suite.
        :return: the set of ppas affected by token deactivations.
        """
        # First we grab all the active tokens for which there is a
        # matching current archive subscription for a team of which the
        # token owner is a member.
        store = IStore(ArchiveSubscriber)
        valid_tokens = store.find(
            ArchiveAuthToken,
            ArchiveAuthToken.date_deactivated == None,
            ArchiveAuthToken.archive_id == ArchiveSubscriber.archive_id,
            ArchiveSubscriber.status == ArchiveSubscriberStatus.CURRENT,
            ArchiveSubscriber.subscriber_id == TeamParticipation.teamID,
            TeamParticipation.personID == ArchiveAuthToken.person_id)

        # We can then evaluate the invalid tokens by the difference of
        # all active tokens and valid tokens.
        all_active_tokens = store.find(
            ArchiveAuthToken,
            ArchiveAuthToken.date_deactivated == None)
        invalid_tokens = all_active_tokens.difference(valid_tokens)

        # We note the ppas affected by these token deactivations so that
        # we can later update their htpasswd files.
        affected_ppas = set()
        for token in invalid_tokens:
            if send_email:
                self.sendCancellationEmail(token)
            token.deactivate()
            affected_ppas.add(token.archive)

        return affected_ppas

    def expireSubscriptions(self):
        """Expire subscriptions as necessary.

        If an `ArchiveSubscriber`'s date_expires has passed, then
        set its status to EXPIRED.
        """
        now = datetime.now(pytz.UTC)

        store = IStore(ArchiveSubscriber)
        newly_expired_subscriptions = store.find(
            ArchiveSubscriber,
            ArchiveSubscriber.status == ArchiveSubscriberStatus.CURRENT,
            ArchiveSubscriber.date_expires != None,
            ArchiveSubscriber.date_expires <= now)

        subscription_names = [
            subs.displayname for subs in newly_expired_subscriptions]
        if subscription_names:
            newly_expired_subscriptions.set(
                status=ArchiveSubscriberStatus.EXPIRED)
            self.logger.info(
                "Expired subscriptions: %s" % ", ".join(subscription_names))

    def getNewTokensSinceLastRun(self):
        """Return result set of new tokens created since the last run."""
        store = IStore(ArchiveAuthToken)
        # If we don't know when we last ran, we include all active
        # tokens by default.
        last_success = getUtility(IScriptActivitySet).getLastActivity(
            'generate-ppa-htaccess')
        extra_expr = []
        if last_success:
            # NTP is running on our servers and therefore we can assume
            # only minimal skew, we include a fudge-factor of 1s so that
            # even the minimal skew cannot demonstrate bug 627608.
            last_script_start_with_skew = last_success.date_started - (
                timedelta(seconds=1))
            extra_expr = [
                ArchiveAuthToken.date_created >= last_script_start_with_skew]

        new_ppa_tokens = store.find(
            ArchiveAuthToken,
            ArchiveAuthToken.date_deactivated == None,
            *extra_expr)

        return new_ppa_tokens

    def _getValidTokensForPPAs(self, ppas):
        """Returns a dict keyed by archive with all the tokens for each."""
        affected_ppas_with_tokens = dict([
            (ppa, []) for ppa in ppas])

        store = IStore(ArchiveAuthToken)
        affected_ppa_tokens = store.find(
            ArchiveAuthToken,
            ArchiveAuthToken.date_deactivated == None,
            ArchiveAuthToken.archive_id.is_in(
                [ppa.id for ppa in ppas]))

        for token in affected_ppa_tokens:
            affected_ppas_with_tokens[token.archive].append(token)

        return affected_ppas_with_tokens

    def getNewPrivatePPAs(self):
        """Return the recently created private PPAs."""
        # Avoid circular import.
        from lp.soyuz.model.archive import Archive
        store = IStore(Archive)
        # If we don't know when we last ran, we include all active
        # tokens by default.
        last_success = getUtility(IScriptActivitySet).getLastActivity(
            'generate-ppa-htaccess')
        extra_expr = []
        if last_success:
            extra_expr = [
                Archive.date_created >= last_success.date_completed]

        return store.find(
            Archive, Archive._private == True, *extra_expr)

    def main(self):
        """Script entry point."""
        self.logger.info('Starting the PPA .htaccess generation')
        self.expireSubscriptions()
        affected_ppas = self.deactivateTokens(send_email=True)

        # In addition to the ppas that are affected by deactivated
        # tokens, we also want to include any ppas that have tokens
        # created since the last time we ran.
        for token in self.getNewTokensSinceLastRun():
            affected_ppas.add(token.archive)

        affected_ppas.update(self.getNewPrivatePPAs())

        affected_ppas_with_tokens = {}
        if affected_ppas:
            affected_ppas_with_tokens = self._getValidTokensForPPAs(
                affected_ppas)

        for ppa, valid_tokens in affected_ppas_with_tokens.iteritems():
            # If this PPA is blacklisted, do not touch it's htaccess/pwd
            # files.
            blacklisted_ppa_names_for_owner = self.blacklist.get(
                ppa.owner.name, [])
            if ppa.name in blacklisted_ppa_names_for_owner:
                self.logger.info(
                    "Skipping htacess updates for blacklisted PPA "
                    " '%s' owned by %s.",
                        ppa.name,
                        ppa.owner.displayname)
                continue
            elif ppa.status == ArchiveStatus.DELETED or ppa.enabled is False:
                self.logger.info(
                    "Skipping htacess updates for deleted or disabled PPA "
                    " '%s' owned by %s.",
                        ppa.name,
                        ppa.owner.displayname)
                continue

            self.ensureHtaccess(ppa)
            temp_htpasswd = self.generateHtpasswd(ppa, valid_tokens)
            if not self.replaceUpdatedHtpasswd(ppa, temp_htpasswd):
                os.remove(temp_htpasswd)

        if self.options.no_deactivation or self.options.dryrun:
            self.logger.info('Dry run, so not committing transaction.')
            self.txn.abort()
        else:
            self.logger.info('Committing transaction...')
            self.txn.commit()

        self.logger.info('Finished PPA .htaccess generation')
