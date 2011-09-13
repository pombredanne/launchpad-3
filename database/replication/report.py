#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate a report on the replication setup.

This report spits out whatever we consider useful for checking up on and
diagnosing replication. This report will grow over time, and maybe some
bits of this will move to seperate monitoring systems or reports.

See the Slony-I documentation for more discussion on the data presented
by this report.
"""

__metaclass__ = type
__all__ = []

import _pythonpath

from cgi import escape as html_escape
from cStringIO import StringIO
from optparse import OptionParser
import sys

from canonical.database.sqlbase import connect, quote_identifier, sqlvalues
from canonical.launchpad.scripts import db_options
import replication.helpers


class Table:
    labels = None # List of labels to render as the first row of the table.
    rows = None # List of rows, each row being a list of strings.

    def __init__(self, labels=None):
        if labels is None:
            self.labels = []
        else:
            self.labels = labels[:]
        self.rows = []


class HtmlReport:

    def alert(self, text):
        """Return text marked up to be noticed."""
        return '<span style="alert">%s</span>' % html_escape(text)

    def table(self, table):
        """Return the rendered table."""
        out = StringIO()
        print >> out, "<table>"
        if table.labels:
            print >> out, "<tr>"
            for label in table.labels:
                print >> out, "<th>%s</th>" % html_escape(unicode(label))
            print >> out, "</tr>"

        for row in table.rows:
            print >> out, "<tr>"
            for cell in row:
                print >> out, "<td>%s</td>" % html_escape(unicode(cell))
            print >> out, "</tr>"

        print >> out, "</table>"

        return out.getvalue()


class TextReport:
    def alert(self, text):
        return text

    def table(self, table):
        max_col_widths = []
        for label in table.labels:
            max_col_widths.append(len(label))
        for row in table.rows:
            row = list(row) # We need len()
            for col_idx in range(0,len(row)):
                col = row[col_idx]
                max_col_widths[col_idx] = max(
                    len(str(row[col_idx])), max_col_widths[col_idx])

        out = StringIO()
        for label_idx in range(0, len(table.labels)):
            print >> out, table.labels[label_idx].ljust(
                max_col_widths[label_idx]),
        print >> out
        for width in max_col_widths:
            print >> out, '='*width,
        print >> out
        for row in table.rows:
            row = list(row)
            for col_idx in range(0, len(row)):
                print >> out, str(row[col_idx]).ljust(max_col_widths[col_idx]),
            print >> out
        print >> out

        return out.getvalue()


def node_overview_report(cur, options):
    """Dumps the sl_node table in a human readable format.

    This report tells us which nodes are active and which are inactive.
    """
    report = options.mode()
    table = Table(["Node", "Comment", "Active"])

    cur.execute("""
        SELECT no_id, no_comment, no_active
        FROM sl_node
        ORDER BY no_comment
        """)
    for node_id, node_comment, node_active in cur.fetchall():
        if node_active:
            node_active_text = 'Active'
        else:
            node_active_text = report.alert('Inactive')
        table.rows.append([
            'Node %d' % node_id, node_comment, node_active_text])

    return report.table(table)


def paths_report(cur, options):
    """Dumps the sl_paths table in a human readable format.

    This report describes how nodes will attempt to connect to each other
    if they need to, allowing you to sanity check the settings and pick up
    obvious misconfigurations that would stop Slony daemons from being able
    to connect to one or more nodes, blocking replication.
    """
    report = options.mode()
    table = Table(["From client node", "To server node", "Via connection"])

    cur.execute("""
        SELECT pa_client, pa_server, pa_conninfo
        FROM sl_path
        ORDER BY pa_client, pa_server
        """)
    for row in cur.fetchall():
        table.rows.append(row)

    return report.table(table)


def listen_report(cur, options):
    """Dumps the sl_listen table in a human readable format.

    This report shows you the tree of which nodes a node needs to check
    for events on.
    """
    report = options.mode()
    table = Table(["Node", "Listens To", "Via"])

    cur.execute("""
        SELECT li_receiver, li_origin, li_provider
        FROM sl_listen
        ORDER BY li_receiver, li_origin, li_provider
        """)
    for row in cur.fetchall():
        table.rows.append(['Node %s' % node for node in row])
    return report.table(table)


def subscribe_report(cur, options):
    """Dumps the sl_subscribe table in a human readable format.

    This report shows the subscription tree - which nodes provide
    a replication set to which subscriber.
    """

    report = options.mode()
    table = Table([
        "Set", "Is Provided By", "Is Received By",
        "Is Forwardable", "Is Active"])
    cur.execute("""
        SELECT sub_set, sub_provider, sub_receiver, sub_forward, sub_active
        FROM sl_subscribe ORDER BY sub_set, sub_provider, sub_receiver
        """)
    for set_, provider, receiver, forward, active in cur.fetchall():
        if active:
            active_text = 'Active'
        else:
            active_text = report.alert('Inactive')
        table.rows.append([
            "Set %d" % set_, "Node %d" % provider, "Node %d" % receiver,
            str(forward), active_text])
    return report.table(table)


def tables_report(cur, options):
    """Dumps the sl_table table in a human readable format.

    This report shows which tables are being replicated and in which
    replication set. It also importantly shows the internal Slony id used
    for a table, which is needed for slonik scripts as slonik is incapable
    of doing the tablename -> Slony id mapping itself.
    """
    report = options.mode()
    table = Table(["Set", "Schema", "Table", "Table Id"])
    cur.execute("""
        SELECT tab_set, nspname, relname, tab_id, tab_idxname, tab_comment
        FROM sl_table, pg_class, pg_namespace
        WHERE tab_reloid = pg_class.oid AND relnamespace = pg_namespace.oid
        ORDER BY tab_set, nspname, relname
        """)
    for set_, namespace, tablename, table_id, key, comment in cur.fetchall():
        table.rows.append([
            "Set %d" % set_, namespace, tablename, str(table_id)])
    return report.table(table)


def sequences_report(cur, options):
    """Dumps the sl_sequences table in a human readable format.

    This report shows which sequences are being replicated and in which
    replication set. It also importantly shows the internal Slony id used
    for a sequence, which is needed for slonik scripts as slonik is incapable
    of doing the tablename -> Slony id mapping itself.
    """
    report = options.mode()
    table = Table(["Set", "Schema", "Sequence", "Sequence Id"])
    cur.execute("""
        SELECT seq_set, nspname, relname, seq_id, seq_comment
        FROM sl_sequence, pg_class, pg_namespace
        WHERE seq_reloid = pg_class.oid AND relnamespace = pg_namespace.oid
        ORDER BY seq_set, nspname, relname
        """)
    for set_, namespace, tablename, table_id, comment in cur.fetchall():
        table.rows.append([
            "Set %d" % set_, namespace, tablename, str(table_id)])
    return report.table(table)


def main():
    parser = OptionParser()

    parser.add_option(
        "-f", "--format", dest="mode", default="text",
        choices=['text', 'html'],
        help="Output format MODE", metavar="MODE")
    db_options(parser)

    options, args = parser.parse_args()

    if options.mode == "text":
        options.mode = TextReport
    elif options.mode == "html":
        options.mode = HtmlReport
    else:
        assert False, "Unknown mode %s" % options.mode

    con = connect()
    cur = con.cursor()

    cur.execute(
            "SELECT TRUE FROM pg_namespace WHERE nspname=%s"
            % sqlvalues(replication.helpers.CLUSTER_NAMESPACE))

    if cur.fetchone() is None:
        parser.error(
                "No Slony-I cluster called %s in that database"
                % replication.helpers.CLUSTERNAME)
        return 1


    # Set our search path to the schema of the cluster we care about.
    cur.execute(
            "SET search_path TO %s, public"
            % quote_identifier(replication.helpers.CLUSTER_NAMESPACE))

    print node_overview_report(cur, options)
    print paths_report(cur, options)
    print listen_report(cur, options)
    print subscribe_report(cur, options)
    print tables_report(cur, options)
    print sequences_report(cur, options)


if __name__ == '__main__':
    sys.exit(main())
