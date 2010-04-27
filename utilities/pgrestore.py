#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Restore a full database dump. This script should become unnecessary
when we are running PostgreSQL 8 as it will correctly order its dumps.
"""

import sys, os, tempfile
from optparse import OptionParser
from subprocess import Popen, PIPE
from signal import SIGTERM

class DumpFile(object):
    """File-like object wrapping a normal or compressed file on disk"""
    process = None

    def __init__(self, dumpname):

        if dumpname.endswith('.bz2'):
            self.process = Popen(
                    ["bunzip2", "-c", dumpname], stdin=PIPE, stdout=PIPE
                    )
        elif dumpname.endswith('.gz'):
            self.process = Popen(
                    ["gunzip", "-c", dumpname], stdin=PIPE, stdout=PIPE
                    )
        else:
            self.out = open(dumpname, 'r')

        if self.process is not None:
            self.process.stdin.close()
            self.out = self.process.stdout

    def read(self, bytes=None):
        return self.out.read(bytes)

    def close(self):
        if self.process is None:
            return self.out.close()

        if self.process.poll() is not None:
            if self.process.returncode != 0:
                print >> sys.stderr, "ERROR: Uncompressor returned %d" % (
                        self.process.returncode
                        )
            return

        os.kill(self.process.pid, SIGTERM)

    def fileno(self):
        return self.out.fileno()


def generate_order(dumpname):
    """Generate a correctly order dump listing"""
   
    dump_input = DumpFile(dumpname)
    cmd = Popen('pg_restore -l', shell=True, stdout=PIPE, stdin=dump_input)
    (stdout, stderr) = cmd.communicate()
    if cmd.returncode != 0:
        raise RuntimeError('pg_restore returned %d' % rv)
    dump_input.close()

    full_listing = [l for l in stdout.split('\n') if l.strip()]

    full_listing.sort(listing_cmp)

    return '\n'.join(full_listing)


def listing_cmp(a, b):
    if POSTGRESQL7:
        idx = 2
    else:
        idx = 3
    if a.startswith(';'):
        atype = ';'
    else:
        atype = a.split()[idx]

    if b.startswith(';'):
        btype = ';'
    else:
        btype = b.split()[idx]

    # Build indexes in same parse as tables, so that tables with constraints
    # that need to reference other tables (eg. CHECK is_person() columns)
    # load in a reasonable time. This is more fragile, but should last
    # until postgresql 8 migration makes this script irrelevant.
    scores = {
        ';': 0,
        'SCHEMA': 1,
        'TYPE': 10,
        'FUNC': 10,
        'PROCEDURAL': 10,
        'FUNCTION': 10,
        'OPERATOR': 20,
        'TABLE': 30,
        'SEQUENCE': 35,
        'BLOBS': 38,
        'VIEW': 40,
        'TRIGGER': 90,
        'FK': 95,
        'CONSTRAINT': 95,
        'INDEX': 30,
        'COMMENT': 200,
        'ACL': 1000,
        }

    # Will fail if we get an unknown type in the listing, which is by design
    # at the moment. Might want a default value though instead?
    return cmp(scores[atype], scores[btype])


def createdb(options):
    args = ['createdb', '--encoding=UNICODE']

    if options.user:
        args.append('--username=%s' % options.user)

    if options.host:
        args.append('--host=%s' % options.host)

    args.append(options.dbname)

    if options.verbose:
        cmd = ' '.join(args)
        print >> sys.stderr, 'Running %s' % cmd
        createdb = Popen(args)
    else:
        createdb = Popen(args, stdout=PIPE, stderr=PIPE)

    (out, err) = createdb.communicate()

    if createdb.returncode != 0:
        print >> sys.stderr, err
        print >> sys.stderr, out
        print >> sys.stderr, 'ERROR: %d' % createdb.returncode
        sys.exit(createdb.returncode)


if __name__ == "__main__":

    parser = OptionParser("usage: %prog [options] [DUMPFILE | -]")
    parser.add_option(
            "-d", "--dbname", dest="dbname",
            help="Create the database DBNAME and restore the dump into it",
            metavar="DBNAME"
            )
    parser.add_option(
            "-H", "--host", dest="host", default=None,
            help="Connect to PostgreSQL running on HOST",
            metavar="HOST"
            )
    parser.add_option(
            "--no-acl", dest="perms", action="store_false",
            default=True, help="Do not restore ownership or permissions",
            )
    parser.add_option(
            "-U", "--user", dest="user",
            help="Connect as superuser USER", metavar="USER", default=None
            )
    parser.add_option(
            "-v", "--verbose", dest="verbose",
            action="store_true", default=False
            )
    parser.add_option(
            "-7", dest="postgres7",
            action="store_true", default=False,
            help="Restore into a PostgreSQL 7.4 database"
            )

    (options, args) = parser.parse_args()

    if options.postgres7:
        POSTGRESQL7 = True
    else:
        POSTGRESQL7 = False

    if len(args) > 1:
        parser.error("Too many arguments")

    if len(args) == 0:
        parser.error("Must specify dump file name.")

    dumpname = args[0]

    if not os.path.exists(dumpname):
        parser.error("%s does not exist" % dumpname)

    handle, listingfilename = tempfile.mkstemp()
    try:
        os.close(handle)
        listingfile = open(listingfilename, 'w')
        listingfile.write(generate_order(dumpname))
        listingfile.close()

        pg_restore_args = ["pg_restore", "--use-list=%s" % listingfilename]

        if options.dbname:
            createdb(options)
            pg_restore_args.append("--dbname=%s" % options.dbname)

        if not options.perms:
            pg_restore_args.append("--no-owner")
            pg_restore_args.append("--no-acl")

        if options.user:
            pg_restore_args.append("--user=%s" % options.user)

        if options.host:
            pg_restore_args.append("--host=%s" % options.host)

        if options.verbose:
            pg_restore_args.append("--verbose")

        dump_input = DumpFile(dumpname)

        if options.verbose:
            cmd = ' '.join(pg_restore_args)
            print >> sys.stderr, "Running %s" % cmd
            rest = Popen(pg_restore_args, stdin=dump_input)
        else:
            rest = Popen(pg_restore_args, stderr=PIPE, stdin=dump_input)

        (out,err) = rest.communicate()
        if rest.returncode != 0:
            print >> sys.stderr, err
            print >> sys.stderr, 'ERROR: %d' % rest.returncode
            sys.exit(rest.returncode)

    finally:
        os.unlink(listingfilename)


