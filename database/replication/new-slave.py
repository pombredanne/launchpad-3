#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Bring a new slave online."""

__metaclass__ = type
__all__ = []

import _pythonpath

from optparse import OptionParser
import re
import sys
import time
from textwrap import dedent

from canonical.database.sqlbase import connect
from canonical.launchpad.scripts import db_options, logger_options, logger

import helpers

def main():
    parser = OptionParser(
        "Usage: %prog [options] node_id connection_string")

    db_options(parser)
    logger_options(parser)

    options, args = parser.parse_args()

    log = logger(options, 'new-slave')

    if len(args) != 2:
        parser.error("Missing required arguments.")

    node_id, connection_string = args

    try:
        node_id = int(node_id)
    except ValueError:
        parser.error("node_id must be a positive integer.")
    if node_id <= 0:
        parser.error("node_id must be a positive integer.")

    existing_nodes = helpers.get_all_cluster_nodes(connect('slony'))

    if node_id in [node.node_id for node in existing_nodes]:
        parser.error("Node %d already exists in the cluster." % node_id)

    if re.search(r'\buser', connection_string, re.I):
        parser.error("Don't include username in connection string.")

    slony_connection_string = "%s user=slony" % connection_string

    comment = 'New node created %s' % time.ctime()

    script = dedent("""\
        define new_node %d;
        define new_node_conninfo '%s';
        node @new_node admin conninfo = @new_node_conninfo;

        echo 'Initializing new node.';
        try {
            store node (id=@new_node, comment='%s');
            echo 'Creating new node paths.';
        """ % (node_id, slony_connection_string, comment))

    for node in existing_nodes:
        nickname = node.nickname
        script += dedent("""\
            store path (
                server=@%(nickname)s, client=@new_node,
                conninfo=@%(nickname)s_conninfo);
            store path (
                server=@new_node, client=@%(nickname)s,
                conninfo=@new_node_conninfo);
            """ % vars())

    script += dedent("""\
        } on error { echo 'Failed.'; exit 1; }

        echo 'Waiting for sync.';
        sync (id = @master_node);
        wait for event (
            origin = ALL, confirmed = ALL,
            wait on = @master_node, timeout = 0);

        echo 'Subscribing new node to main replication set.';
        subscribe set (
            id=@lpmain_set, provider=@master_node, receiver=@new_node);

        echo 'Waiting for sync... this might take a while...';
        sync (id = @master_node);
        wait for event (
            origin = ALL, confirmed = ALL,
            wait on = @master_node, timeout = 0);
        """)

    helpers.execute_slonik(script)

    helpers.validate_replication(connect('slony').cursor())

    return 0

if __name__ == '__main__':
    sys.exit(main())
