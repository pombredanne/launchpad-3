#!/usr/bin/python2.4

# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

import crypt, filecmp, os, tempfile
from operator import attrgetter

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.archive import IArchiveSet
from canonical.launchpad.interfaces.archiveauthtoken import (
    IArchiveAuthTokenSet)
from canonical.launchpad.interfaces.archivesubscriber import (
    IArchiveSubscriberSet)
from canonical.launchpad.scripts.base import LaunchpadCronScript


HTACCESS_TEMPLATE = """
AuthType           Basic
AuthName           "Token Required"
AuthUserFile       .htpasswd
Require            valid-user
"""

BUILDD_USER_NAME = "buildd"


class HtaccessTokenGenerator(LaunchpadCronScript):
    """Helper class for generating .htaccess files for private PPAs."""

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

    def writeHtpasswd(self, filename, list_of_users):
        """Write out a new htpasswd file.

        :param filename: The file to create.
        :param list_of_users: A list of (user, password, salt) tuples.
        """
        if os.path.isfile(filename):
            os.remove(filename)

        file = open(filename, "a")
        for entry in list_of_users:
            user, password, salt = entry
            encrypted = crypt.crypt(password, salt)
            file.write("%s:%s\n" % (user, encrypted))

        file.close()

    def ensureHtaccess(self, ppa):
        """Generate a .htaccess for `ppa`."""
        if self.options.dryrun:
            return

        # The publisher Config object does not have an
        # interface, so we need to remove the security wrapper.
        pub_config = removeSecurityProxy(ppa.getPubConfig())
        htaccess_filename = os.path.join(pub_config.htaccessroot, ".htaccess")
        if not os.path.isfile(htaccess_filename):
            # It's not there, so create it.
            file = open(htaccess_filename, "w")
            file.write(HTACCESS_TEMPLATE)
            file.close()
            self.logger.debug("Created .htaccess for %s" % ppa.title)

    def generateHtpasswd(self, ppa, tokens):
        """Generate a htpasswd file for `ppa`s `tokens`.
        
        :param ppa: The context PPA (an `IArchive`).
        :param tokens: A iterable containing `IArchiveAuthToken`s.
        :return: The filename of the htpasswd file that was generated.
        """
        # Create a temporary file that will be a new .htpasswd.
        fd, temp_filename = tempfile.mkstemp()

        # The first .htpasswd entry is the buildd_secret.
        list_of_users = [
            (BUILDD_USER_NAME, ppa.buildd_secret, BUILDD_USER_NAME[:2])]

        # Iterate over tokens and write the appropriate htpasswd
        # entries for them.  Use a consistent sort order so that the
        # generated file can be compared to an existing one later.
        for token in sorted(tokens, key=attrgetter("id")):
            entry = (token.person.name, token.token, token.person.name[:2])
            list_of_users.append(entry)

        self.writeHtpasswd(temp_filename, list_of_users)

        return temp_filename

    def replaceUpdatedHtpasswd(self, ppa, temp_htpasswd_file):
        """Compare the new and the old htpasswd and replace if changed.
        
        :return: True if the file was replaced.
        """
        if self.options.dryrun:
            return False

        # The publisher Config object does not have an
        # interface, so we need to remove the security wrapper.
        pub_config = removeSecurityProxy(ppa.getPubConfig())
        htpasswd_filename = os.path.join(pub_config.htaccessroot, ".htpasswd")

        if (not os.path.isfile(htpasswd_filename) or
            not filecmp.cmp(htpasswd_filename, temp_htpasswd_file)):
            # Atomically replace the old file or create a new file.
            os.rename(temp_htpasswd_file, htpasswd_filename)
            self.logger.debug("Replaced htpasswd for %s" % ppa.title)
            return True

        return False

    def deactivateTokens(self, ppa):
        """Deactivate tokens as necessary.

        If a subscriber no longer has an active token for the PPA, we
        deactivate it.

        :param ppa: The PPA to check tokens for.
        :return: a list of valid tokens.
        """
        tokens = getUtility(IArchiveAuthTokenSet).getByArchive(ppa)
        valid_tokens = []
        for token in tokens:
            result = getUtility(
                IArchiveSubscriberSet).getBySubscriberWithActiveToken(
                    token.person, ppa)
            if result.count() == 0:
                # The subscriber's token is no longer active,
                # deactivate it.
                token.deactivate()
            else:
                valid_tokens.append(token)
        return valid_tokens

    def main(self):
        """Script entry point."""
        self.logger.info('Starting the PPA .htaccess generation')
        ppas = getUtility(IArchiveSet).getPrivatePPAs()
        for ppa in ppas:
            valid_tokens = self.deactivateTokens(ppa)
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

