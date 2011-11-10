# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Find OOPS References within the LP database."""

__metaclass__ = type

__all__ = [
    'referenced_oops',
    ]

import re

from canonical.database.sqlbase import (
    cursor,
    sqlvalues,
    )


def referenced_oops(start_date, end_date, context_clause, context_params):
    '''Return a set of OOPS codes that are referenced somewhere in the
    Launchpad database.

    We currently check the entire Message store, Bugs, BugTasks and Question
    '''
    # Note that the POSIX regexp syntax is subtly different to the Python,
    # and that we need to escape all \ characters to keep the SQL interpreter
    # happy.
    posix_oops_match = (r"~* '^(oops\\s*-\\s*\\w+)"
        r"|(\\moops\\s*-\\s*\\w+)'")
    params = dict(start_date=start_date, end_date=end_date)
    params.update(context_params)
    sql_params = sqlvalues(**params)
    sql_params['posix_oops_match'] = posix_oops_match
    query = ("""
        WITH recent_messages AS
            (SELECT id FROM Message WHERE
             datecreated BETWEEN %(start_date)s AND %(end_date)s)
        SELECT DISTINCT subject FROM Message
        WHERE subject %(posix_oops_match)s AND subject IS NOT NULL
            AND id IN (SELECT id FROM recent_messages)
        UNION ALL
        SELECT content FROM MessageChunk WHERE content %(posix_oops_match)s
            AND message IN (SELECT id FROM recent_messages)
        UNION ALL
        SELECT title || ' ' || description
        FROM Bug WHERE
            date_last_updated BETWEEN %(start_date)s AND %(end_date)s AND
            (title %(posix_oops_match)s OR description %(posix_oops_match)s)
        UNION ALL
        SELECT title || ' ' || description || ' ' || COALESCE(whiteboard,'')
        FROM Question WHERE """ + context_clause + """
            AND (datelastquery BETWEEN %(start_date)s AND %(end_date)s
                OR datelastresponse BETWEEN %(start_date)s AND %(end_date)s)
            AND (title %(posix_oops_match)s
                OR description %(posix_oops_match)s
                OR whiteboard %(posix_oops_match)s)
        """) % sql_params

    referenced_codes = set()
    oops_re = re.compile(r'(?i)(?P<oops>\boops-\w+)')

    cur = cursor()
    cur.execute(query)
    for content in (row[0] for row in cur.fetchall()):
        for oops in oops_re.findall(content):
            referenced_codes.add(oops.upper())

    return referenced_codes
