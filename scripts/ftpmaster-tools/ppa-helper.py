#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.


# pylint: disable-msg=W0403
import _pythonpath

import os

from storm.locals import Join
from storm.store import Store
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.database.archive import Archive
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory)
from canonical.launchpad.helpers import emailPeople
from canonical.launchpad.interfaces.archive import ArchivePurpose
from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.webapp import canonical_url


class PPAHelperScript(LaunchpadScript):

    description = "PPA management actions."

    def add_my_options(self):
        self.parser.add_option(
            '-o', '--output', metavar='FILENAME', action='store',
            type='string', dest='output', default='output.csv',
            help='Where to store the output')
        self.parser.add_option(
            '--gen-over-quota', action='store_true', default=False,
            help='Generate PPAs over-quota list.')
        self.parser.add_option(
            '--gen-user-emails', action='store_true', default=False,
            help='Generate active PPA user email list')
        self.parser.add_option(
            '--gen-orphan-repos', action='store_true', default=False,
            help='Generate PPAs orphan repositories list.')


    def getActivePPAs(self):
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        store = Store.of(ubuntu)
        origin = (
            Archive,
            Join(SourcePackagePublishingHistory,
                 SourcePackagePublishingHistory.archive == Archive.id),)
        results = store.using(*origin).find(
            Archive,
            Archive.distribution == ubuntu,
            Archive.purpose == ArchivePurpose.PPA,
            Archive.enabled == True)
        results.order_by(Archive.date_created)
        return list(results.config(distinct=True))

    def main(self):
        if self.options.gen_over_quota:
            self.generateOverQuotaReport()
        elif self.options.gen_user_emails:
            self.generateUserEmailsReport()
        elif self.options.gen_orphan_repos:
            self.generateOrphanRepos()
        else:
            self.logger.error('No action selected.')

        self.logger.info('Done')

    def generateOverQuotaReport(self):
        active_ppas = self.getActivePPAs()
        self.logger.info(
            'Generating over-quota list for %d active PPAs.'
            % len(active_ppas))

        fd = open(self.options.output, 'w')
        for ppa in active_ppas:
            limit = ppa.authorized_size
            size = ppa.estimated_size / (2 ** 20)
            if size <= (.80 * limit):
                continue
            values = (
                canonical_url(ppa),
                str(limit),
                str(size),
                )
            line = ' | '.join(values).encode('utf-8')
            fd.write(line + '\n')
        fd.close()

    def generateUserEmailsReport(self):
        active_ppas = self.getActivePPAs()
        self.logger.info(
            'Generating user email list for %d active PPAs.'
            % len(active_ppas))

        people_to_email = set()
        for ppa in active_ppas:
            people_to_email.update(emailPeople(ppa.owner))

        fd = open(self.options.output, 'w')
        for user in people_to_email:
            values = (
                user.name,
                user.displayname,
                user.preferredemail.email,
                )
            line = ' | '.join(values).encode('utf-8')
            fd.write(line + '\n')
        fd.close()

    def generateOrphanRepos(self):
        active_ppas = [
            ppa for ppa in self.getActivePPAs() if not ppa.private]
        self.logger.info(
            'Calculating orphan repositories list for %d active PPAs.'
            % len(active_ppas))

        active_paths = set(
            ppa.owner.name for ppa in active_ppas)

        root = config.personalpackagearchive.root
        existing_paths = set(
            os.listdir(config.personalpackagearchive.root))
        self.logger.info(
            'Checking %d repositories in %s.' % (len(existing_paths), root))

        orphan_paths = existing_paths - active_paths
        self.logger.info(
            'Found %d orphan repositories:' % len(orphan_paths))

        for orphan in orphan_paths:
            self.logger.info('\t%s' % os.path.join(root, orphan))

        missing_paths = active_paths - existing_paths
        self.logger.info(
            'Found %d missing repositories:' % len(missing_paths))

        for missing in missing_paths:
            self.logger.info('\t%s' % os.path.join(root, missing))


if __name__ == '__main__':
    script = PPAHelperScript('ppahelper', dbuser='ro')
    script.run()
