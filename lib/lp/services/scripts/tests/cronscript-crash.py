#!/usr/bin/python -S
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cronscript that raises an unhandled exception."""

__metaclass__ = type
__all__ = []

import _pythonpath

from lp.services.scripts.base import LaunchpadCronScript

from canonical.launchpad.webapp.errorlog import globalErrorUtility


class CrashScript(LaunchpadCronScript):

    def main(self):
        initial_oops = globalErrorUtility.getLastOopsReport().id
        self.logger.debug("This is debug level")
        self.logger.warn("This is a warning")

        first_oops = globalErrorUtility.getLastOopsReport().id
        if first_oops != initial_oops:
            self.logger.info("New OOPS detected")

        self.logger.critical("This is critical")

        second_oops = globalErrorUtility.getLastOopsReport().id
        if second_oops != first_oops:
            self.logger.info("New OOPS detected")

        raise NotImplementedError("Whoops")


if __name__ == "__main__":
    script = CrashScript("crash")
    script.lock_and_run()
