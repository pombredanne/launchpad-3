#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Process LinkChecker .csv results for the staging server, stuff them into
a database and generate a report suitable for spamming developers with.
"""

__metaclass__ = type

# pylint: disable-msg=W0403
import _pythonpath

import csv, re, sys
from StringIO import StringIO
from optparse import OptionParser
from sqlobject import StringCol, IntCol, BoolCol, FloatCol, DatabaseIndex
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW
from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.lp import initZopeless
from canonical.database.sqlbase import SQLBase
from canonical.config import config
from lp.services.mail.sendmail import simple_sendmail


class CheckedLink(SQLBase):
    _table = 'CheckedLink'
    urlname = StringCol(notNull=True)
    recursionlevel = IntCol(notNull=True)
    parentname = StringCol(notNull=True)
    baseref = StringCol(notNull=True)
    result = StringCol(notNull=True)
    resultcode = IntCol(notNull=True)
    warningstring = StringCol(notNull=True)
    infostring = StringCol(notNull=True)
    valid = BoolCol(notNull=True)
    url = StringCol(notNull=True, unique=True, alternateID=True)
    line = IntCol(notNull=True)
    col = IntCol(notNull=True)
    name = StringCol(notNull=True)
    dltime = FloatCol()
    dlsize = IntCol()
    checktime = FloatCol(notNull=True)
    brokensince = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    #cached = BoolCol(notNull=True)

    resultcode_index = DatabaseIndex('resultcode')
    recursionlevel_index = DatabaseIndex('recursionlevel')


def main(csvfile, log):

    # Where we store broken links
    broken = set()

    # Suck in the csv file, updating the database and adding to the broken set
    reader = csv.DictReader(
            (line.replace('\0','') for line in csvfile
                if not line.startswith('#'))
            )
    for row in reader:
        # Get the result code
        if row['valid']:
            row['resultcode'] = 200
            row['result'] = '200 Ok'
        else:
            m = re.search('^(\d+)', row['result'] or '')
            if m is None:
                if row['result'] == 'URL is empty':
                    continue
                elif 'The read operation timed out' in row['result']:
                    row['result'] = '601 %s' % row['result']
                    row['resultcode'] = 601
                else:
                    row['result'] = '602 %s' % row['result']
                    row['resultcode'] = 602
            else:
                row['resultcode'] = int(m.group(1))

        # Cast input and nuke crap (to avoid confusing SQLObject)
        row['recursionlevel'] = int(row['recursionlevel'])
        row['valid'] = row['valid'] in ('True', 'true')
        row['line'] = int(row['line'])
        row['col'] = int(row['column']) # Renamed - column is a SQL keyword
        del row['column']
        row['dltime'] = float(row['dltime'])
        row['dlsize'] = int(row['dlsize'])
        row['checktime'] = float(row['checktime'])
        del row['cached']
        if row['resultcode'] < 400:
            row['brokensince'] = None

        try:
            link = CheckedLink.byUrl(row['url'])
            link.set(**row)
        except LookupError:
            link = CheckedLink(**row)
        broken.add(link)

    total = len(broken)

    # Delete any entries that were not spidered
    # XXX StuartBishop 2005-07-04: Only if older than a threshold.
    for link in CheckedLink.select():
        if link in broken:
            continue
        link.destroySelf()

    new_broken_links = CheckedLink.select("""
        resultcode in (404, 500, 601)
        AND brokensince > CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            - '1 day 12 hours'::interval
        """, orderBy=["recursionlevel", "parentname", "url"])

    rep = report("New Arrivals", new_broken_links, total, brokensince=False)

    old_broken_links = CheckedLink.select("""
        resultcode in (404, 500, 601)
        AND brokensince <= CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            - '1 day 12 hours'::interval
        AND brokensince >
            CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - '14 days'::interval
        """, orderBy=["recursionlevel", "parentname", "url"])

    rep += report("Old Favorites", old_broken_links, total, brokensince=True)

    antique_broken_links = CheckedLink.select("""
        resultcode in (404, 500, 601)
        AND brokensince <=
            CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - '14 days'::interval
        """, orderBy=["brokensince", "recursionlevel", "parentname", "url"])

    rep += report(
            "Hall of Shame", antique_broken_links, total, brokensince=True
            )

    if not options.email:
        # Print to stdout in system encoding - might raise UnicodeError on
        # some systems. Tough.
        print rep
    else:
        # Override this setting - we are only here if email explicitly
        # requested on the command line.
        send_email_data = """
            [zopeless]
            send_email: True
            """
        config.push('send_email_data', send_email_data)
        simple_sendmail(
                "noreply@canonical.com", [options.email], options.subject,
                rep, {'Keywords': 'LinkChecker', 'X-Fnord': 'Fnord'}
                )
        config.pop('send_email_data')


def report(title, links, total, brokensince=True):

    out = StringIO()

    heading = "%s (%d/%d)" % (title, links.count(), total)
    print >> out, heading
    print >> out, "=" * len(heading)

    def print_row(title, value):
        print >> out, "%-7s: %s" % (title, str(value))

    for link in links:
        print_row("Link", link.url)
        print_row("Parent", link.parentname)
        print_row("Result", link.result)
        if link.warningstring:
            print_row("Warning", link.warningstring)
        if brokensince:
            print_row("Since", link.since.strftime('%A %d %B %Y'))
        print >> out
    print >> out

    return out.getvalue()


if __name__ == '__main__':
    parser = OptionParser("Usage: %prog [OPTIONS] [input.csv]")
    db_options(parser)
    logger_options(parser)

    parser.add_option(
            "-c", "--create", action="store_true", dest="create",
            default=False, help="Create the database tables"
            )

    parser.add_option(
            "-s", "--subject", dest="subject", help="Email using SUBJECT",
            metavar="SUBJECT", default="LinkChecker report"
            )

    parser.add_option(
            "-t", "--to", dest="email", help="Email to ADDRESS",
            metavar="ADDRESS", default=None
            )

    options, args = parser.parse_args()

    log = logger(options)

    if len(args) == 0 or args[0] == '-':
        log.debug("Reading from stdin")
        csvfile = sys.stdin
    else:
        csvfile = open(args[0], 'rb')

    ztm = initZopeless()

    if options.create:
        # Create the table if it doesn't exist. Unfortunately, this is broken
        # so we only create the table if requested on the command line
        CheckedLink.createTable(ifNotExists=True)

    main(csvfile, log)
    ztm.commit()

