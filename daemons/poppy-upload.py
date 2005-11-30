#!/usr/bin/python

from canonical.poppy.server import run_server
from canonical.archivepublisher.poppyinterface import PoppyInterface

import sys
import logging

def main():
    args = sys.argv[1:]
    if len(args) != 2:
        print "usage: poppy-upload.py rootuploaddirectory port"
        return 1
    root, port = args
    host = "127.0.0.1"
    ident = "lucille upload server"
    numthreads = 4

    #XXX cprov 20051130: use lp pattern for loghandler
    logger = logging.getLogger('Server')
    hdlr = logging.FileHandler('++lucilleupload.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)

    # command line to invoke uploader
    cmd = [('python scripts/process-upload.py -C insecure '
            '-r warty --no-mails -vv -d'), '@distro@', '@fsroot@'] 

    iface = PoppyInterface(logger, cmd=cmd)
    

    run_server(root, host, int(port), ident, numthreads,
               iface.new_client_hook, iface.client_done_hook,
               iface.auth_verify_hook)
    return 0

if __name__ == '__main__':
    sys.exit(main())
