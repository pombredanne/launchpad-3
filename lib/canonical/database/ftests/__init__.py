
import os
import canonical.lp

def getDBHost():
    # We must look for the PGHOST env var because we'll use it for mktap. If
    # we used it only to create connections we wouldn't need to use it,
    # because it's always used by any module that uses libpq.
    if os.environ.get('PGHOST'):
        dbhost = os.environ.get('PGHOST')
    elif canonical.lp.dbhost:
        dbhost = canonical.lp.dbhost
    else:
        dbhost = 'localhost'

    return dbhost
