#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Copy publications across suites."""

import _pythonpath


from canonical.launchpad.scripts.base import (LaunchpadScript,
    LaunchpadScriptFailure)
from canonical.launchpad.scripts.ftpmaster import (
    PackageCopyError, CopyPackageHelper)
from canonical.lp import READ_COMMITTED_ISOLATION


class CopyPackage(LaunchpadScript):

    usage = '%prog -s warty mozilla-firefox --to-suite hoary'
    description = 'MOVE or COPY a published package to another suite.'

    def add_my_options(self):

        self.parser.add_option(
            '-n', '--dry-run', dest='dryrun', default=False,
            action='store_true', help='Do not commit changes.')

        self.parser.add_option(
            '-y', '--confirm-all', dest='confirm_all',
            default=False, action='store_true',
            help='Do not prompt the user for questions.')

        self.parser.add_option(
            '-c', '--comment', dest='comment', default='',
            action='store', help='Copy comment.')

        self.parser.add_option(
            '-b', '--include-binaries', dest='include_binaries',
            default=False, action='store_true',
            help='Whether to copy related binaries or not')

        self.parser.add_option(
            '-d', '--from-distribution', dest='from_distribution_name',
            default='ubuntu', action='store',
            help='Optional source distribution.')

        self.parser.add_option(
            '--to-distribution', dest='to_distribution_name',
            default='ubuntu', action='store',
            help='Optional destination distribution.')

        self.parser.add_option(
            '-s', '--from-suite', dest='from_suite', default=None,
            action='store', help='Optional source suite.')

        self.parser.add_option(
            '--to-suite', dest='to_suite', default=None,
            action='store', help='Optional destination suite.')

        self.parser.add_option(
            '-e', '--sourceversion', dest='sourceversion', default=None,
            action='store',
            help='Optional Source Version, defaults to the current version.')

    def main(self):

        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)

        if len(self.args) != 1:
            raise LaunchpadScriptFailure(
                "At least one non-option argument must be given, "
                "the sourcename.")

        copy_helper = CopyPackageHelper(
            sourcename=self.args[0],
            sourceversion=self.options.sourceversion,
            from_suite=self.options.from_suite,
            to_suite=self.options.to_suite,
            from_distribution_name=self.options.from_distribution_name,
            to_distribution_name=self.options.to_distribution_name,
            confirm_all=self.options.confirm_all,
            comment=self.options.comment,
            include_binaries=self.options.include_binaries,
            logger=self.logger)

        try:
            copy_helper.performCopy()
        except PackageCopyError, err:
            raise LaunchpadScriptFailure(err)

        if copy_helper.synced and not self.options.dryrun:
            self.txn.commit()
        else:
            self.logger.info('Nothing to commit.')
            self.txn.abort()

        self.logger.info('Done.')
        self.logger.info(
            'Archive changes will by applied in the next publishing cycle')
        self.logger.info('Be patient.')


if __name__ == '__main__':
    script = CopyPackage('copy-package', dbuser='lucille')
    script.lock_and_run()

