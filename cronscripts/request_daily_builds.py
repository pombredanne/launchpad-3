#!/usr/bin/python -S
#
# Copyright 2010-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Request builds for stale daily build recipes and snap packages."""

__metaclass__ = type

import _pythonpath

import transaction
from zope.component import getUtility

from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildSource,
    )
from lp.services.config import config
from lp.services.scripts.base import LaunchpadCronScript
from lp.services.webapp.errorlog import globalErrorUtility
from lp.snappy.interfaces.snap import ISnapSet


class RequestDailyBuilds(LaunchpadCronScript):
    """Run create merge proposal jobs."""

    def __init__(self):
        name = 'request_daily_builds'
        dbuser = config.request_daily_builds.dbuser
        LaunchpadCronScript.__init__(self, name, dbuser)

    def main(self):
        globalErrorUtility.configure(self.name)
        source = getUtility(ISourcePackageRecipeBuildSource)
        builds = source.makeDailyBuilds(self.logger)
        self.logger.info('Requested %d daily recipe builds.' % len(builds))
        builds = getUtility(ISnapSet).makeAutoBuilds(self.logger)
        self.logger.info(
            'Requested %d automatic snap package builds.' % len(builds))
        transaction.commit()


if __name__ == '__main__':
    script = RequestDailyBuilds()
    script.lock_and_run()
