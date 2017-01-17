# Copyright 2011-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run a command with a default Xvfb environment

If the command is not found it is searched for in the same directory as this
script. This lets you do `bin/with-xvfb iharness` for example.

Follows sinzui's advice to the launchpad-dev list:
  https://lists.launchpad.net/launchpad-dev/msg07879.html
"""

from __future__ import absolute_import, print_function, unicode_literals

import os
import sys

from lp.services.osutils import find_on_path


def main():
    # Look for the command to run in this script's directory if it's not
    # found along the default PATH.
    args = sys.argv[1:]
    if args and not find_on_path(args[0]):
        nearby = os.path.join(os.path.dirname(sys.argv[0]), args[0])
        if os.access(nearby, os.X_OK):
            args[0] = nearby
    # If no command has been given and SHELL is set, spawn a shell.
    elif not args and os.environ.get("SHELL"):
        args = [os.environ["SHELL"]]

    args = [
        # -ac disables host-based access control mechanisms. See Xserver(1).
        # -screen forces a screen configuration. At the time of writing
        #    there is some disagreement between xvfb-run(1) and Xvfb(1)
        #    about what the default is.
        "--server-args=-ac -screen 0 1024x768x24",
        # Try to get a free server number, starting at 99. See xvfb-run(1).
        "--auto-servernum",
        ] + args
    os.execvp("xvfb-run", args)
