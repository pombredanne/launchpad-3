# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The Poppy daemon."""

__metaclass__ = type
__all__ = [
    'main',
    ]

import optparse
import warnings

from canonical.launchpad.scripts import (
    logger,
    logger_options,
    )
from lp.poppy.hooks import Hooks
from lp.poppy.server import run_server

# XXX: 2010-04-26, Salgado, bug=570246: Silence python2.6 deprecation
# warnings.
warnings.filterwarnings(
    'ignore', '.*(md5|sha|sets)', DeprecationWarning,
    )


def main():
    parser = optparse.OptionParser()
    logger_options(parser)

    parser.add_option("--cmd", action="store", metavar="CMD",
                      help="Run CMD after each upload completion")

    parser.add_option("--allow-user", action="store", metavar="USER",
                      default='ubuntu',
                      help="Username allowed to log in.")

    parser.add_option("--permissions", action="store", metavar="PERMS",
                      default='g+rwxs',
                      help="Permissions to chmod the targetfsroot with "
                      "before letting go of the directory.")

    options, args = parser.parse_args()

    log = logger(options, "poppy-upload")

    if len(args) != 2:
        print "usage: poppy-upload.py rootuploaddirectory port"
        return 1

    root, port = args
    host = "0.0.0.0"
    ident = "lucille upload server"
    numthreads = 4

    hooks = Hooks(root, log, allow_user=options.allow_user, cmd=options.cmd,
                  perms=options.permissions)

    run_server(host, int(port), ident, numthreads,
               hooks.new_client_hook, hooks.client_done_hook,
               hooks.auth_verify_hook)
    return 0


