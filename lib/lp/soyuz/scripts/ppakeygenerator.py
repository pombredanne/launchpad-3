# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'PPAKeyGenerator',
    ]

from zope.component import getUtility

from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey,
    )
from lp.services.scripts.base import (
    LaunchpadCronScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.interfaces.archive import IArchiveSet


class PPAKeyGenerator(LaunchpadCronScript):

    usage = '%prog [-A archive-reference]'
    description = 'Generate a GPG signing key for PPAs.'

    def add_my_options(self):
        self.parser.add_option(
            "-A", "--archive",
            help="The reference of the archive whose key should be generated.")

    def generateKey(self, archive):
        """Generate a signing key for the given archive."""
        self.logger.info(
            "Generating signing key for %s" % archive.displayname)
        archive_signing_key = IArchiveSigningKey(archive)
        archive_signing_key.generateSigningKey()
        self.logger.info("Key %s" % archive.signing_key.fingerprint)

    def main(self):
        """Generate signing keys for the selected PPAs."""
        if self.options.archive is not None:
            archive = getUtility(IArchiveSet).getByReference(
                self.options.archive)
            if archive is None:
                raise LaunchpadScriptFailure(
                    "No archive named '%s' could be found."
                    % self.options.archive)
            if archive.signing_key is not None:
                raise LaunchpadScriptFailure(
                    "%s already has a signing_key (%s)"
                    % (archive.displayname, archive.signing_key.fingerprint))
            archives = [archive]
        else:
            archive_set = getUtility(IArchiveSet)
            archives = list(archive_set.getPPAsPendingSigningKey())

        for archive in archives:
            self.generateKey(archive)
            self.txn.commit()
