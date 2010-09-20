#!/usr/bin/python -S
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cronscript that raises an unhandled exception."""

__metaclass__ = type
__all__ = []

import _pythonpath

from lp.services.scripts.base import LaunchpadCronScript


class CrashScript(LaunchpadCronScript):

    def main(self):
        self.logger.warn("This is a warning")
        raise NotImplementedError("Whoops")


if __name__ == "__main__":
    script = CrashScript("crash")
    script.lock_and_run()
