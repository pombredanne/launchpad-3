/*
Copyright 2009 Canonical Ltd.  This software is licensed under the
GNU Affero General Public License version 3 (see the file LICENSE).

Stored procedures designed for use only by the test suite. These
will not be loaded onto the production database
*/

CREATE OR REPLACE FUNCTION _killall_backends(text)
RETURNS Boolean AS $$
    import os
    from signal import SIGTERM

    plan = plpy.prepare(
        "SELECT procpid FROM pg_stat_activity WHERE datname=$1", ['text']
        )
    success = True
    for row in plpy.execute(plan, args):
        try:
            plpy.info("Killing %d" % row['procpid'])
            os.kill(row['procpid'], SIGTERM)
        except OSError:
            success = False

    return success
$$ LANGUAGE plpythonu;

COMMENT ON FUNCTION _killall_backends(text) IS 'Kill all backend processes connected to the given database. Note that this is unlikely to work if you are connected to the database you are killing, as you are likely to kill your own connection before all the others have been killed.';

