# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

__all__ = [
    'referenced_oops', 'unwanted_oops_files', 'path_to_oopsid',
    'prune_empty_oops_directories',
    ]

from datetime import date, timedelta, datetime
import re
import os

from pytz import utc

from canonical.database.sqlbase import cursor
from canonical.launchpad.webapp import errorlog
from canonical.launchpad.webapp.tales import FormattersAPI

def referenced_oops():
    '''Return a set of OOPS codes that are referenced somewhere in the
    Launchpad database.

    We currently check the entire Message store, Bugs, BugTasks and Question
    '''
    # Note that the POSIX regexp syntax is subtly different to the Python,
    # and that we need to escape all \ characters to keep the SQL interpreter
    # happy.
    posix_oops_match = r"~* '\\moops\\s*-?\\s*\\d*[a-z]+\\d+'"
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
        SELECT statusexplanation FROM BugTask
        WHERE statusexplanation %(posix_oops_match)s
        UNION ALL
        SELECT title || ' ' || description || ' ' || COALESCE(whiteboard,'')
        FROM Question WHERE title %(posix_oops_match)s
            OR description %(posix_oops_match)s
            OR whiteboard %(posix_oops_match)s
        """ % vars()

    referenced_codes = set()

    cur = cursor()
    cur.execute(query)
    for content in (row[0] for row in cur.fetchall()):
        found = False
        for match in FormattersAPI._re_linkify.finditer(content):
            if match.group('oops') is not None:
                code_string = match.group('oopscode')
                referenced_codes.add(code_string.upper())
                found = True
        assert found, \
            'PostgreSQL regexp matched content that Python regexp ' \
            'did not (%r)' % (content,)

    return referenced_codes


def path_to_oopsid(path):
    '''Extract the OOPS id from a path to an OOPS file'''
    date_str = os.path.basename(os.path.dirname(path))
    match = re.search('^(\d\d\d\d)-(\d\d+)-(\d\d+)$', date_str)
    year, month, day = (int(bit) for bit in match.groups())
    oops_id = os.path.basename(path).split('.')[1]
    day = (datetime(year, month, day, tzinfo=utc) - errorlog.epoch).days + 1
    return '%d%s' % (day, oops_id)


def unwanted_oops_files(root_path, days, log=None):
    '''Generate a list of OOPS files that are older than 'days' and are
       not referenced in the Launchpad database.
    '''
    wanted_oops = referenced_oops()

    for oops_path in old_oops_files(root_path, days):
        oopsid = path_to_oopsid(oops_path)
        if oopsid.upper() not in wanted_oops:
            yield oops_path
        elif log is not None:
            log.debug("%s (%s) is wanted" % (oops_path, oopsid))


def old_oops_files(root_path, days):
    '''Generate a list of all OOPS files found under root_path that
       are older than 'days' days old.

       root_path defaults to the config.error_reports.errordir
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
            if re.search(
                    r'^\d+\.[a-zA-Z]+\d+(?:\.gz|\.bz2)?$', filename
                    ) is not None:
                yield os.path.join(dirpath, filename)

def prune_empty_oops_directories(root_path):
    for filename in os.listdir(root_path):
        if re.search(r'^\d\d\d\d-\d\d-\d\d$', filename) is None:
            continue
        path = os.path.join(root_path, filename)
        if not os.path.isdir(path):
            continue
        if os.listdir(path):
            continue
        os.rmdir(path)

