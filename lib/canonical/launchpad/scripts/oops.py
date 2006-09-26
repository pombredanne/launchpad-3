# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from canonical.database.sqlbase import cursor
from canonical.launchpad.webapp.tales import FormattersAPI

def referenced_oops():
    '''Return a set of OOPS codes that are referenced somewhere in the
    Launchpad database.

    We currently check the entire Message store, Bugs, BugTasks and Tickets
    '''
    # Note that the POSIX regexp syntax is subtly different to the Python,
    # and that we need to escape all \ characters to keep the SQL interpreter
    # happy.
    posix_oops_match = r"~* '\\moops\\s*-?\\s*\\d*[a-z]+\\d+'"
    query = """
        SELECT DISTINCT subject FROM Message WHERE subject %(posix_oops_match)s
        UNION ALL
        SELECT content FROM MessageChunk WHERE content %(posix_oops_match)s
        UNION ALL
        SELECT title || ' ' || description || ' ' || name
        FROM Bug WHERE title %(posix_oops_match)s
            OR description %(posix_oops_match)s
            OR name %(posix_oops_match)s
        UNION ALL
        SELECT statusexplanation FROM BugTask
        WHERE statusexplanation %(posix_oops_match)s
        UNION ALL
        SELECT title || ' ' || description || ' ' || whiteboard
        FROM Ticket WHERE title %(posix_oops_match)s
            OR description %(posix_oops_match)s
            OR whiteboard %(posix_oops_match)s
        """ % vars()

    referenced_codes = set()

    cur = cursor()
    cur.execute(query)
    for content in (row[0] for row in cur.fetchall()):
        assert FormattersAPI._re_linkify.search(content) is not None, \
            'PostgreSQL regexp matched content that Python regexp ' \
            'did not (%r)' % (content,)
        for match in FormattersAPI._re_linkify.finditer(content):
            group_dict = match.groupdict()
            assert group_dict.has_key('oops'), \
                'PostgreSQL regexp matched content that Python regexp ' \
                'did not (%r)' % (content,)
            referenced_codes.add(group_dict['oopscode'].upper())

    return referenced_codes
