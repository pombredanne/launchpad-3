#!/usr/bin/python

import sys
import logging
import optparse

from canonical.poppy.server import run_server
from canonical.archivepublisher.poppyinterface import PoppyInterface
from canonical.launchpad.scripts import logger, logger_options


def main():

    parser = optparse.OptionParser()
    logger_options(parser)

    # Do not remove this option, nor its implementation. Tests are using it.
    parser.add_option("--test", action="store_true", default=False,
                      help="Run in test mode and do not process the upload")

    options, args = parser.parse_args()

    log = logger(options, "poppy-upload")

    if len(args) != 2:
        print "usage: poppy-upload.py rootuploaddirectory port"
        return 1

    root, port = args
    host = "127.0.0.1"
    ident = "lucille upload server"
    numthreads = 4
    if not options.test:
        # Command line to invoke uploader (it shares the same PYTHONPATH)
        if options.log_file:
            log_option = "--log-file '%s'" % options.log_file
        else:
            log_option = ''
        cmd = ['python scripts/process-upload.py -C autosync '
               '--no-mails -vv', log_option, '-d', '@distro@', '@fsroot@']
        background = True
    else:
        cmd = None
        background = False
   
    iface = PoppyInterface(log, cmd=cmd, background=background)

    run_server(root, host, int(port), ident, numthreads,
               iface.new_client_hook, iface.client_done_hook,
               iface.auth_verify_hook)
    return 0

if __name__ == '__main__':
    sys.exit(main())
