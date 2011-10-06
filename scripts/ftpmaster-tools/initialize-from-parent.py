#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initialize a new distroseries from its parent series."""

import _pythonpath

import transaction
from zope.component import getUtility

from canonical.config import config
from lp.app.errors import NotFoundError
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.scripts.base import LaunchpadScript, LaunchpadScriptFailure
from lp.soyuz.scripts.initialize_distroseries import (
    InitializationError,
    InitializeDistroSeries,
    )


class InitializeFromParentScript(LaunchpadScript):

    usage = "Usage: %prog [options] <SERIES>"

    def add_my_options(self):
        self.parser.add_option(
            "-N", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help="Whether to treat this as a dry-run or not.")
        self.parser.add_option(
            "-d", "--distro", dest="distribution",
            metavar="DISTRO", default="ubuntu", help="Distribution name")
        self.parser.add_option(
            "-a", "--arches", dest="arches",
            help="A comma-seperated list of arches to limit the child "
            "distroseries to inheriting")

    def main(self):
        if len(self.args) != 1:
            self.parser.error("SERIES is required")

        distroseries_name = self.args[0]

        try:
            # 'ubuntu' is the default option.distribution value
            distribution = getUtility(IDistributionSet)[
                self.options.distribution]
            distroseries = distribution[distroseries_name]
        except NotFoundError, info:
            raise LaunchpadScriptFailure('%s not found' % info)

        try:
            arches = ()
            if self.options.arches is not None:
                arches = tuple(self.options.arches.split(','))
            ids = InitializeDistroSeries(distroseries, arches=arches)
            self.logger.debug("Checking preconditions")
            ids.check()
            self.logger.debug(
                "Initializing from parent(s), copying publishing records.")
            ids.initialize()
        except InitializationError, e:
            transaction.abort()
            raise LaunchpadScriptFailure(e)

        if self.options.dryrun:
            self.logger.debug('Dry-Run mode, transaction aborted.')
            transaction.abort()
        else:
            self.logger.debug('Committing transaction.')
            transaction.commit()


if __name__ == '__main__':
    script = InitializeFromParentScript(
        'initialize-from-parent', config.initializedistroseries.dbuser)
    script.lock_and_run()
