#!/usr/bin/python -S
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate slonik scripts for Slony 1.2 to 2.0 migration.

Remove this script after migration is complete.
"""

__metaclass__ = type
__all__ = []

import _pythonpath

from optparse import OptionParser
import os.path
from textwrap import dedent

from canonical.config import config
from canonical.database.sqlbase import connect
from canonical.launchpad import scripts
import replication.helpers
from replication.helpers import (
    LPMAIN_SET_ID,
    LPMIRROR_SET_ID,
    SSO_SET_ID,
    get_all_cluster_nodes,
    get_master_node,
    )


con = None
options = None

sets = {
    LPMAIN_SET_ID: 'lpmain_set',
    SSO_SET_ID: 'sso_set',
    LPMIRROR_SET_ID: 'lpmirror_set',
    }


def outpath(filename):
    return os.path.join(options.outdir, filename)


def generate_preamble():
    outf = open(outpath('mig_preamble.sk'), 'w')
    print >> outf, replication.helpers.preamble(con)

    cur = con.cursor()

    for set_id, set_name in list(sets.items()):
        cur.execute(
            "SELECT set_origin FROM _sl.sl_set WHERE set_id=%s", [set_id])
        result = cur.fetchone()
        if result:
            origin = result[0]
            print >> outf, "define %s_origin %d;" % (set_name, origin)
        else:
            del sets[set_id] # For testing. Production will have 3 sets.
    outf.close()


def generate_uninstall():
    outf = open(outpath('mig_uninstall.sk'), 'w')
    print >> outf, "# Uninstall Slony-I 1.2 from all nodes"
    print >> outf, "include <mig_preamble.sk>;"

    nodes = get_all_cluster_nodes(con)

    # Ensure everything is really, really synced since we will be
    # resubscribing with 'omit copy'
    for node in nodes:
        print >> outf, dedent("""\
                sync (id=%d);
                wait for event (origin=%d, confirmed=all, wait on=%d);
                """).strip() % (node.node_id, node.node_id, node.node_id)

    for node in nodes:
        print >> outf, "uninstall node (id=%d);" % node.node_id
    outf.close()


def generate_sync():
    outf = open(outpath('mig_sync.sk'), 'w')
    print >> outf, "sync (id=1);"
    print >> outf, "wait for event (origin=1, confirmed=all, wait on=1);"
    outf.close()


def generate_rebuild():
    outf = open(outpath('mig_rebuild.sk'), 'w')
    print >> outf, "# Rebuild the replication cluster with Slony-I 2.0"
    print >> outf, "include <mig_preamble.sk>;"

    nodes = get_all_cluster_nodes(con)
    first_node = nodes[0]
    remaining_nodes = nodes[1:]

    # Initialize the cluster
    print >> outf, "init cluster (id=%d);" % first_node.node_id

    # Create all the other nodes
    for node in remaining_nodes:
        print >> outf, "store node (id=%d, event node=%d);" % (
            node.node_id, first_node.node_id)

    # Create paths so they can communicate.
    for client_node in nodes:
        for server_node in nodes:
            print >> outf, (
                "store path (server=%d, client=%d, "
                "conninfo=@node%d_node_conninfo);" % (
                    server_node.node_id, client_node.node_id,
                    server_node.node_id))

    # sync to ensure replication is happening.
    print >> outf, "include <mig_sync.sk>;"

    # Create replication sets.
    for set_id, set_name in sets.items():
        generate_initialize_set(set_id, set_name, outf)
    print >> outf, "include <mig_sync.sk>;"

    # Subscribe slave nodes to replication sets.
    for set_id, set_name in sets.items():
        generate_subscribe_set(set_id, set_name, outf)

    outf.close()


def generate_initialize_set(set_id, set_name, outf):
    origin_node = get_master_node(con, set_id)
    print >> outf, "create set (id=%d, origin=%d, comment='%s');" % (
        set_id, origin_node.node_id, set_name)
    cur = con.cursor()
    cur.execute("""
        SELECT tab_id, tab_nspname, tab_relname, tab_comment
        FROM _sl.sl_table WHERE tab_set=%s
        """, (set_id,))
    for tab_id, tab_nspname, tab_relname, tab_comment in cur.fetchall():
        if not tab_comment:
            tab_comment=''
        print >> outf, dedent("""\
                set add table (
                    set id=%d, origin=%d, id=%d,
                    fully qualified name='%s.%s',
                    comment='%s');
                """).strip() % (
                    set_id, origin_node.node_id, tab_id,
                    tab_nspname, tab_relname, tab_comment)
    cur.execute("""
        SELECT seq_id, seq_nspname, seq_relname, seq_comment
        FROM _sl.sl_sequence WHERE seq_set=%s
        """, (set_id,))
    for seq_id, seq_nspname, seq_relname, seq_comment in cur.fetchall():
        if not seq_comment:
            seq_comment=''
        print >> outf, dedent("""\
                set add sequence (
                    set id=%d, origin=%d, id=%d,
                    fully qualified name='%s.%s',
                    comment='%s');
                """).strip() % (
                    set_id, origin_node.node_id, seq_id,
                    seq_nspname, seq_relname, seq_comment)


def generate_subscribe_set(set_id, set_name, outf):
    origin_node = get_master_node(con, set_id)
    cur = con.cursor()
    cur.execute("""
        SELECT sub_receiver FROM _sl.sl_subscribe
        WHERE sub_set=%s and sub_active is true
        """, (set_id,))
    for receiver_id, in cur.fetchall():
        print >> outf, dedent("""\
                subscribe set (
                    id=%d, provider=%d, receiver=%d,
                    forward=true, omit copy=true);
                wait for event (
                    origin=%d, confirmed=all, wait on=%d);
                """).strip() % (
                    set_id, origin_node.node_id, receiver_id,
                    origin_node.node_id, origin_node.node_id)
        print >> outf, "include <mig_sync.sk>;"


def main():
    parser = OptionParser()
    scripts.db_options(parser)
    parser.add_option(
        "-o", "--output-dir", dest='outdir', default=".",
        help="Write slonik scripts to DIR", metavar="DIR")
    global options
    options, args = parser.parse_args()
    if args:
        parser.error("Too many arguments")
    scripts.execute_zcml_for_scripts(use_web_security=False)

    global con
    con = connect()

    generate_preamble()
    generate_sync()
    generate_uninstall()
    generate_rebuild()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
