#!/usr/bin/python2.6 -S
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Full update process."""

import _pythonpath

import os.path
from optparse import OptionParser
import subprocess
import sys

from canonical.launchpad.scripts import (
    db_options,
    logger_options,
    )


def run_script(script, *extra_args):
    script_path = os.path.join(os.path.dirname(__file__), script)
    return subprocess.call([script_path] + sys.argv[1:] + list(extra_args))


def main():
    parser = OptionParser()

    # Add all the command command line arguments.
    db_options(parser)
    logger_options(parser)
    (options, args) = parser.parse_args()
    if args:
        parser.error("Too many arguments")

    preflight_rc = run_script('preflight.py')
    if preflight_rc != 0:
        return preflight_rc

    upgrade_rc = run_script('upgrade.py')
    if upgrade_rc != 0:
        return upgrade_rc

    fti_rc = run_script('fti.py')
    if fti_rc != 0:
        return fti_rc

    security_rc = run_script('security.py', '--cluster')
    if security_rc != 0:
        return security_rc

    preflight_rc = run_script('preflight.py')
    return preflight_rc


if __name__ == '__main__':
    sys.exit(main())
