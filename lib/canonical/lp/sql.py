from zope.app import zapi
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from zope.app.rdb.interfaces import IZopeConnection, IZopeCursor

def confirmEncoding(*args,**kw):
    rdb = zapi.getUtility(IZopeDatabaseAdapter, 'launchpad')
    dsn = rdb.getDSN()
    dbname = str(dsn.split('/')[-1])
    con = IZopeConnection(rdb())
    cur = IZopeCursor(con.cursor())
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
