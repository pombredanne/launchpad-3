# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Sanity checks for the PostgreSQL database"""

__metaclass__ = type


from canonical.config import config
from canonical.database.sqlbase import connect


def confirmEncoding(*args, **kw):
    '''Raise an exception, explaining what went wrong, if the PostgreSQL
    database encoding is not UNICODE

    subsribed to zope.app.appsetup.IProcessStartingEvent

    '''
    con = connect(config.launchpad.dbuser)
    try:
        cur = con.cursor()
        dbname = config.database.dbname
        cur.execute(
            'select encoding from pg_catalog.pg_database where datname=%s',
            (dbname,)
            )
        res = cur.fetchall()
        if len(res) != 1:
            raise RuntimeError('Database %r does not exist or is not unique'
                    % (dbname,)
                    )
        if res[0][0] != 6:
            raise RuntimeError(
                "Database %r is using the wrong encidong (%r). You need "
                "to recreate your database using 'createdb -E UNICODE %s'" % (
                    dbname, res[0][0], dbname
                    )
                )
    finally:
        con.close()

def confirmNoAddMissingFrom(*args, **kw):
    '''Raise a warning if add_missing_from is turned on (dangerous default).

    This will become an error in the future. Subscribed to
    zope.app.appsetup.IProcessStartingEvent

    '''
    con = connect(config.launchpad.dbuser)
    try:
        cur = con.cursor()
        cur.execute('show add_missing_from')
        res = cur.fetchall()
        if res[0][0] != 'off':
            raise RuntimeError(
                    "Need to set add_missing_from=false in "
                    "/etc/postgresql/postgresql.conf"
                    )
    finally:
        con.close()
