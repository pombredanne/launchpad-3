#!/usr/bin/python2.4
# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
"""
Apply all outstanding schema patches to an existing launchpad database
"""

__metaclass__ = type

import _pythonpath # Sort PYTHONPATH

import glob
import os.path
from optparse import OptionParser
import re
import subprocess
import sys
import tempfile
from textwrap import dedent
import time

from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.database.sqlbase import connect, connect_string

SLONY_CLUSTER = 'lpcluster'

def main():
    schema_dir = os.path.dirname(__file__)

    con = connect(options.dbuser)

    if options.slonik:
        slonik_preamble(options.slonik)

    # trusted.sql contains all our stored procedures, which may be required
    # for patches to apply correctly so must be run first.
    apply_other(con, 'trusted.sql')

    dbpatches = applied_patches(con)

    # Generate a list of all patches we might want to apply
    patches = []
    all_patch_files = glob.glob(
            os.path.join(schema_dir, 'patch-???-??-?.sql'))
    all_patch_files.sort()
    for patch_file in all_patch_files:
        m = re.search('patch-(\d\d\d)-(\d\d)-(\d).sql$', patch_file)
        if m is None:
            log.fatal('Invalid patch filename %s' % repr(patch_file))
            sys.exit(1)

        major, minor, patch = [int(i) for i in m.groups()]
        if (major, minor, patch) in dbpatches:
            continue # This patch has already been applied
        log.debug("Found patch %d.%d.%d -- %s" % (
            major, minor, patch, patch_file
            ))
        patches.append(((major, minor, patch), patch_file))

    # Apply the patches
    for (major, minor, patch), patch_file in patches:
        if options.slonik:
            slonik_apply_path(major, minor, patch, patch_file)
        else:
            apply_patch(con, major, minor, patch, patch_file)

    # Update comments.
    apply_comments(con)

    # Commit changes
    if options.commit:
        log.debug("Committing changes")
        con.commit()


def applied_patches(con):
    """Return a list of all patches that have been applied to the database.
    """
    cur = con.cursor()
    cur.execute("SELECT major, minor, patch FROM LaunchpadDatabaseRevision")
    return [tuple(row) for row in cur.fetchall()]


def apply_patch(con, major, minor, patch, patch_file):
    log.info("Applying %s" % patch_file)
    cur = con.cursor()
    full_sql = open(patch_file).read()

    # Strip comments
    full_sql = re.sub('(?xms) \/\* .*? \*\/', '', full_sql)
    full_sql = re.sub('(?xm) ^\s*-- .*? $', '', full_sql)

    # Regular expression to extract a single statement.
    # A statement may contain semicolons if it is a stored procedure
    # definition, which requires a disgusting regexp or a parser for
    # PostgreSQL specific SQL.
    statement_re = re.compile(
            r"( (?: [^;$] | \$ (?! \$) | \$\$.*? \$\$)+ )",
            re.DOTALL | re.MULTILINE | re.VERBOSE
            )
    for sql in statement_re.split(full_sql):
        sql = sql.strip()
        if sql and sql != ';':
            cur.execute(sql) # Will die on a bad patch.

    # Ensure the patch updated LaunchpadDatabaseRevision. We could do this
    # automatically and avoid the boilerplate, but then we would lose the
    # ability to easily apply the patches manually.
    if (major, minor, patch) not in applied_patches(con):
        log.fatal("%s failed to update LaunchpadDatabaseRevision correctly"
                % patch_file)
        sys.exit(2)

    # Commit changes if we allow partial updates.
    if options.commit and options.partial:
        log.debug("Committing changes")
        con.commit()


def apply_other(con, script):
    log.info("Applying %s" % script)
    if options.slonik:
        slonik_execute_script(options.slonik, script)
    else:
        cur = con.cursor()
        path = os.path.join(os.path.dirname(__file__), script)
        sql = open(path).read()
        cur.execute(sql)

        if options.commit and options.partial:
            log.debug("Committing changes")
            con.commit()

def apply_comments(con):
    if not options.slonik:
        apply_other(con, 'comments.sql')
    else:
        # Split the comments into < 1000 statement limit chunks as required
        # by slonik.
        comments = re.findall(
                "(?ms).*?'\s*;\s*$", open('comments.sql', 'r').read())
        comment_dir = tempfile.mkdtemp()
        counter = 1
        while comments:
            chunk_path = os.path.join(
                    comment_dir, 'comments_%d.sql' % counter)
            chunk_file = open(chunk_path, 'w')
            print >> chunk_file, '\n'.join(comments[:1000])
            del comments[:1000]
            chunk_file.close()
            counter += 1
            slonik_execute_script(options.slonik, chunk_path)


def slonik_preamble(outf):
    #proc = subprocess.Popen(
    #        ['slonik_print_preamble'], stdout=subprocess.PIPE,
    #        stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    #(out, err) = proc.communicate()
    #assert proc.returncode == 0, 'slonik_print_preamble failed: %s' % err
    #print >> options.slonik, out

    print >> outf, "# slonik script for %s" % (connect_string('slony'),)
    print >> outf, "# generated by %s %s\n" % (
            os.path.basename(sys.argv[0]), time.ctime())
    print >> outf, dedent("""\
            cluster name = %s;
            node 1 admin conninfo='%s';
            """ % (SLONY_CLUSTER, connect_string('slony')))


def slonik_execute_script(outf, script_filename):
    replication_set = 1
    master_node = 1
    print >> outf, dedent("""\
        echo 'Executing script %s';
        execute script (
            set id = %d,
            filename = '%s',
            event node = %d
        );
        """ % (
            script_filename, replication_set,
            os.path.abspath(script_filename), master_node))

if __name__ == '__main__':
    parser = OptionParser()
    db_options(parser)
    logger_options(parser)
    parser.add_option(
            "-n", "--dry-run", dest="commit", default=True,
            action="store_false", help="Don't actually commit changes"
            )
    parser.add_option(
            "-p", "--partial", dest="partial", default=False,
            action="store_true",
            help="Commit after applying each patch",
            )
    parser.add_option(
            "-k", "--slonik", dest="slonik", default=None,
            metavar="FILE", help="Output a slonik script to FILE")
    (options, args) = parser.parse_args()

    if args:
        parser.error("Too many arguments")

    if options.commit is False and options.slonik:
        parser.error("--dry-run does not make sense with --slonik")

    if options.partial is True and options.slonik:
        parser.error("--partial cannot be used with --slonik")

    if options.slonik:
        # Open the file for out slonik script. Use '-' for stdout.
        if options.slonik == '-':
            options.slonik = sys.stdout
        else:
            options.slonik = open(options.slonik, 'w')

    log = logger(options)
    main()
