#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Generate a report on the replication setup."""

import _pythonpath

from cgi import escape as html_escape
from cStringIO import StringIO
from optparse import OptionParser
import sys

from canonical.database.sqlbase import connect, quote_identifier, sqlvalues
from canonical.launchpad.scripts import db_options

__metaclass__ = type
__all__ = []


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


def node_overview_report(cur, options):

    report = HtmlReport()
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

    report = HtmlReport()
    table = Table(["From client node", "To server node", "Via connection"])

    cur.execute("""
        SELECT pa_client, pa_server, pa_conninfo
        FROM sl_path
        ORDER BY pa_client, pa_server
        """)
    for row in cur.fetchall():
        table.rows.append(row)

    return report.table(table)


def main():
    parser = OptionParser()

    # Default should be pulled from a config file.
    parser.add_option(
            "-c", "--cluster", dest="cluster", default="dev",
            help="Report on cluster CLUSTER_NAME", metavar="CLUSTER_NAME")
    db_options(parser)

    options, args = parser.parse_args()

    cluster_schema = "_%s" % options.cluster

    con = connect(options.dbuser)
    cur = con.cursor()

    # Check if the Slony schema exists to validate the --cluster option.
    cur.execute(
            "SELECT TRUE FROM pg_namespace WHERE nspname=%s"
            % sqlvalues(cluster_schema))

    if cur.fetchone() is None:
        parser.error(
                "No Slony-I cluster called %s in that database"
                % options.cluster)
        return 1


    # Set our search path to the schema of the cluster we care about.
    cur.execute(
            "SET search_path TO %s, public" % quote_identifier(cluster_schema))

    print node_overview_report(cur, options)
    print paths_report(cur, options)


if __name__ == '__main__':
    sys.exit(main())
