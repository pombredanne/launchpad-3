# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from datetime import date, timedelta
import re
import os
import os.path

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
            code_string = group_dict['oopscode']
            just_the_code = re.search(
                    '(?i)([a-z]+\d+)$', code_string
                    ).group(1).upper()
            referenced_codes.add(just_the_code)

    return referenced_codes


def unwanted_oops_files(root_path, days):
    '''Generate a list of OOPS files that are older than 'days' and are
       not referenced in the Launchpad database.
    '''
    wanted_oops = referenced_oops()

    for oops_path in old_oops_files(root_path, days):
        oops_filename = os.path.basename(oops_path)
        timestamp, oops_code = oops_filename.split('.', 1)
        if oops_code not in wanted_oops:
            yield oops_path


def old_oops_files(root_path, days):
    '''Generate a list of all OOPS files found under root_path that
       are older than 'days' days old.
    
       root_path defaults to the config.launchpad.errorreports.errordir
    '''
    now = date.today()
    for (dirpath, dirnames, filenames) in os.walk(root_path):

        # Only recurse into correctly named OOPS report directories that
        # are more than 'days' days old.
        all_dirnames = dirnames[:]
        del dirnames[:]
        for subdir in all_dirnames:
            date_match = re.search(r'^(\d\d\d\d)-(\d\d)-(\d\d)$', subdir)
            if date_match is None:
                continue

            # Skip if he directory is too new.
            year, month, day = (int(bit) for bit in date_match.groups())
            oops_date = date(year, month, day)
            if now - oops_date <= timedelta(days=days):
                continue

            dirnames.append(subdir)

        # Yield out OOPS filenames
        for filename in filenames:
            if re.search(r'(?i)^\d+\.[a-z]+\d+$', filename) is not None:
                yield os.path.join(dirpath, filename)

