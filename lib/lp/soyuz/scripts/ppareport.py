# Copyright 2009 Canonical Ltd.  All rights reserved.
"""PPA report tool

Generate several reports about the PPA repositories.

 * Over-quota
 * Users emails
 * Orphan repositories (need disk acces on the PPA host machine)
 * Missing repositories (need disk acces on the PPA host machine)
"""

import operator
import os
import sys

from storm.locals import Join
from storm.store import Store
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.helpers import emailPeople
from canonical.launchpad.webapp import canonical_url
from lp.services.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from lp.registry.interfaces.distribution import IDistributionSet


class PPAReportScript(LaunchpadScript):

    description = "PPA report tool."
    output = None

    def add_my_options(self):
        self.parser.add_option(
            '-p', '--ppa', dest='archive_owner_name', action='store',
            help='Archive owner name in case of PPA operations')

        self.parser.add_option(
            '-o', '--output', metavar='FILENAME', action='store',
            type='string', dest='output', default=None,
            help='Optional file to store output.')

        self.parser.add_option(
            '-t', '--quota-threshould', dest='quota_threshould',
            action='store', type=float, default=80,
            help='Quota threshould percentage, defaults to 80 %%')

        self.parser.add_option(
            '--gen-over-quota', action='store_true', default=False,
            help='Generate PPAs over-quota list.')

        self.parser.add_option(
            '--gen-user-emails', action='store_true', default=False,
            help='Generate active PPA user email list')

        self.parser.add_option(
            '--gen-orphan-repos', action='store_true', default=False,
            help='Generate PPAs orphan repositories list.')

        self.parser.add_option(
            '--gen-missing-repos', action='store_true', default=False,
            help='Generate PPAs missing repositories list.')

    def getActivePPAs(self):
        """Return a list of active PPAs for 'ubuntu'.

        if `self.options.archive_owner_name` is defined only return PPAs
        with matching owner names.

        :return: a list of `IArchive` objects.
        """
        # Avoiding circular imports.
        from lp.soyuz.interfaces.archive import ArchivePurpose
        from lp.soyuz.model.archive import Archive
        from lp.soyuz.model.publishing import SourcePackagePublishingHistory
        from lp.registry.model.person import Person

        distribution = getUtility(IDistributionSet).getByName('ubuntu')
        store = Store.of(distribution)
        origin = [
            Archive,
            Join(SourcePackagePublishingHistory,
                 SourcePackagePublishingHistory.archive == Archive.id),
            ]
        clauses = [
            Archive.distribution == distribution,
            Archive.purpose == ArchivePurpose.PPA,
            Archive.enabled == True,
            ]

        owner_name = self.options.archive_owner_name
        if owner_name is not None:
            origin.append(Join(Person, Archive.owner == Person.id))
            clauses.append(Person.name == owner_name)

        results = store.using(*origin).find(
            Archive, *clauses)
        results.order_by(Archive.date_created)

        return list(results.config(distinct=True))

    def setOutput(self):
        """Set the output file descriptor.

        If the 'output' options was passed open a file named as its
        content, otherwise use `sys.stdout`.
        """
        if self.options.output is not None:
            self.logger.info('Report file: %s' % self.options.output)
            self.output = open(self.options.output, 'w')
        else:
            self.output = sys.stdout

    def closeOutput(self):
        """Closes the `output` file descriptor """
        self.output.close()

    def checkOptions(self):
        """Verify if the given command-line options are sane."""
        if ((self.options.gen_orphan_repos or
             self.options.gen_missing_repos or
             self.options.gen_over_quota) and
            self.options.gen_user_emails):
            raise LaunchpadScriptFailure(
                'Users-list cannot be combined with other reports.')

        if ((self.options.gen_orphan_repos or
             self.options.gen_missing_repos) and
            self.options.archive_owner_name is not None):
            raise LaunchpadScriptFailure(
                'Cannot calculate repository paths for a single PPA.')

    def main(self):
        self.checkOptions()

        ppas = self.getActivePPAs()
        self.logger.info('Considering %d active PPAs.' % len(ppas))

        self.setOutput()

        if self.options.gen_over_quota:
            self.reportOverQuota(ppas)

        if self.options.gen_user_emails:
            self.reportUserEmails(ppas)

        if self.options.gen_orphan_repos:
            self.reportOrphanRepos(ppas)

        if self.options.gen_missing_repos:
            self.reportMissingRepos(ppas)

        self.closeOutput()

        self.logger.info('Done')

    def reportOverQuota(self, ppas):
        self.output.write(
            '\n= PPAs over %.2f%% of their quota =\n' %
            self.options.quota_threshould)
        threshould = self.options.quota_threshould / 100.0
        for ppa in ppas:
            limit = ppa.authorized_size
            size = ppa.estimated_size / (2 ** 20)
            if size <= (threshould * limit):
                continue
            values = (
                canonical_url(ppa),
                str(limit),
                str(size),
                )
            line = ' | '.join(values).encode('utf-8')
            self.output.write(line + '\n')

    def reportUserEmails(self, ppas):
        self.output.write('\n= PPA user emails =\n')
        people_to_email = set()
        for ppa in ppas:
            people_to_email.update(emailPeople(ppa.owner))
        sorted_people_to_email = sorted(
            people_to_email, key=operator.attrgetter('name'))
        for user in sorted_people_to_email:
            values = (
                user.name,
                user.displayname,
                user.preferredemail.email,
                )
            line = ' | '.join(values).encode('utf-8')
            self.output.write(line + '\n')

    def _calculatePPAPaths(self, ppas):
        active_paths = set(ppa.owner.name for ppa in ppas)
        existing_paths = set(
            os.listdir(config.personalpackagearchive.root))
        return active_paths, existing_paths

    def reportOrphanRepos(self, ppas):
        self.output.write('\n= Orphan PPA repositories =\n')
        active_paths, existing_paths = self._calculatePPAPaths(ppas)
        orphan_paths = existing_paths - active_paths
        for orphan in sorted(orphan_paths):
            repo_path = os.path.join(
                config.personalpackagearchive.root, orphan)
            self.output.write('%s\n' % repo_path)

    def reportMissingRepos(self, ppas):
        self.output.write('\n= Missing PPA repositories =\n')
        active_paths, existing_paths = self._calculatePPAPaths(ppas)
        missing_paths = active_paths - existing_paths
        for missing in sorted(missing_paths):
            repo_path = os.path.join(
                config.personalpackagearchive.root, missing)
            self.output.write('%s\n' % repo_path)

