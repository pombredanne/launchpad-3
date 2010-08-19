#! /usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Check that all the launchpad scripts and cronscripts run.

Usage hint:

% utilities/check-scripts.py
"""
# pylint: disable-msg=W0403
import _pythonpath

import os
import sys

from lp.services.scripts.tests import find_lp_scripts
from lp.testing import run_script


def check_script(script_path):
    """Run the given script in a subprocess and report its result.

    Check if the script successfully runs if 'help' is requested via
    command line argument ('-h').
    """
    sys.stdout.write('Checking: %s ' % script_path)
    sys.stdout.flush()
    cmd_line = script_path + " -h"
    out, err, returncode = run_script(cmd_line)
    if returncode != os.EX_OK:
        sys.stdout.write('... FAILED\n')
        sys.stdout.write('%s\n' % err)
    else:
        sys.stdout.write('... OK\n')
    sys.stdout.flush()


def main():
    """Walk over the specified script locations and check them."""
    for script_path in find_lp_scripts():
        check_script(script_path)


if __name__ == '__main__':
    sys.exit(main())
