# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Find OOPS References within the LP database."""

__metaclass__ = type

__all__ = [
    'referenced_oops',
    ]

from datetime import (
    date,
    datetime,
    timedelta,
    )
import os
import re

from oops_datedir_repo import serializer
from pytz import utc

from canonical.database.sqlbase import cursor
from canonical.launchpad.webapp.dbpolicy import SlaveOnlyDatabasePolicy
from lp.app.browser.stringformatter import FormattersAPI


def referenced_oops():
    '''Return a set of OOPS codes that are referenced somewhere in the
    Launchpad database.

    We currently check the entire Message store, Bugs, BugTasks and Question
    '''
    # Note that the POSIX regexp syntax is subtly different to the Python,
    # and that we need to escape all \ characters to keep the SQL interpreter
    # happy.
    posix_oops_match = (r"~* '^(oops\\s*-\\s*\\w+)"
        "|[^=]+(\\moops\\s*-\\s*\\w+)'")
    query = """
        SELECT DISTINCT subject FROM Message
        WHERE subject %(posix_oops_match)s AND subject IS NOT NULL
        UNION ALL
        SELECT content FROM MessageChunk WHERE content %(posix_oops_match)s
        UNION ALL
        SELECT title || ' ' || description
        FROM Bug WHERE title %(posix_oops_match)s
            OR description %(posix_oops_match)s
        UNION ALL
        SELECT title || ' ' || description || ' ' || COALESCE(whiteboard,'')
        FROM Question WHERE title %(posix_oops_match)s
            OR description %(posix_oops_match)s
            OR whiteboard %(posix_oops_match)s
        """ % {'posix_oops_match': posix_oops_match}

    referenced_codes = set()

    with SlaveOnlyDatabasePolicy():
        cur = cursor()
        cur.execute(query)
        for content in (row[0] for row in cur.fetchall()):
            for match in FormattersAPI._re_linkify.finditer(content):
                if match.group('oops') is not None:
                    code_string = match.group('oopscode')
                    referenced_codes.add('OOPS-' + code_string.upper())

    return referenced_codes
