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

    options, args = parser.parse_args()

    log = logger(options, "poppy-upload")

    if len(args) != 2:
        print "usage: poppy-upload.py rootuploaddirectory port"
        return 1

    root, port = args
    host = "127.0.0.1"
    ident = "lucille upload server"
    numthreads = 4
    # runs for all incomming uploads:
    # process-upload with "autosync" policy, NO EMAIL SENDING, 
    # verbosely and logging in the some file poppy is logging.
    # '@distro@' and '@fsroot@' are replaced internally according
    # each upload.
    cmdline = ('python2.4 scripts/process-upload.py -C autosync --no-mails '
               '-vv --log-file %s -d @distro@ @fsroot@' % options.log_file)
    cmd = cmdline.split()
   
    iface = PoppyInterface(log, cmd=cmd)

    run_server(root, host, int(port), ident, numthreads,
               iface.new_client_hook, iface.client_done_hook,
               iface.auth_verify_hook)
    return 0

if __name__ == '__main__':
    sys.exit(main())




