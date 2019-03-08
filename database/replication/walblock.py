#!/usr/bin/python
#
# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Feed stdin to stout, blocking if there are too many unshipped WAL files"""

__metaclass__ = type
__all__ = []

from glob import glob
from optparse import OptionParser
import os.path
import sys
import time


def main():
    parser = OptionParser()
    parser.add_option(
        "-n", dest="num_ready", metavar="N", type="int",
        help="Block if there are more than N unshipped WAL files.", default=25)
    parser.add_option(
        "-d", dest="wal_dir", metavar="DIR", type="string",
        help="Path to pg_wal directory",
        default="/var/lib/postgresql/10/main/pg_wal")
    parser.add_option(
        "-v", "--verbose", action="store_true", default=False, help="Verbose")
    options, args = parser.parse_args()
    if args:
        parser.error('Too many arguments')

    chunk_size = 1024 * 1024

    ready_wal_glob = os.path.join(options.wal_dir, 'archive_status', '*.ready')

    while True:
        notified = False
        while len(glob(ready_wal_glob)) > options.num_ready:
            if options.verbose and not notified:
                notified = True
                print >> sys.stderr, 'Blocking on {0} unshipped WAL'.format(
                    len(glob(ready_wal_glob))),
            time.sleep(5)
        if options.verbose and notified:
            print >> sys.stderr, '... Done'

        chunk = sys.stdin.read(chunk_size)
        if chunk == '':
            sys.stdout.flush()
            return 0
        sys.stdout.write(chunk)


if __name__ == '__main__':
    raise SystemExit(main())
