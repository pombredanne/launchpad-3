from zope.app import zapi
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from zope.app.rdb.interfaces import IZopeConnection, IZopeCursor

from warnings import warn

def _cursor():
    rdb = zapi.getUtility(IZopeDatabaseAdapter, 'launchpad')
    dsn = rdb.getDSN()
    dbname = str(dsn.split('/')[-1])
    con = IZopeConnection(rdb())
    cur = IZopeCursor(con.cursor())
    return (dbname, cur)
 
def confirmEncoding(*args, **kw):
    '''Raise an exception, explaining what went wrong, if the PostgreSQL
    database encoding is not UNICODE

    subsribed to zope.app.appsetup.IProcessStartingEvent

    '''
    dbname, cur = _cursor()
    cur.execute(
            'select encoding from pg_catalog.pg_database where datname=%s',
            (dbname,)
            )
    res = cur.fetchall()
    assert len(res) == 1, \
            'Database %r does not exist or is not unique' % (dbname,)
    assert res[0][0] == 6, (
            "Database %r is using the wrong character set (%r). You need to "
            "recreate your database using 'createdb -E UNICODE %s'" % (
                dbname, res[0][0], dbname
                )
            )

def confirmNoAddMissingFrom(*args, **kw):
    '''Raise a warning if add_missing_from is turned on (dangerous default).

    This will become an error in the future. Subscribed to 
    zope.app.appsetup.IProcessStartingEvent

    '''
    dbname, cur = _cursor()
    cur.execute('show add_missing_from')
    res = cur.fetchall()
    assert len(res) == 1, 'Invalid PostgreSQL version? Wierd error'

    msg='Need to set add_missing_from=false in /etc/postgresql/postgresql.conf'
    if res[0][0] != 'off':
        warn(msg, FutureWarning)

