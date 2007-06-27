# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""List all team members: name, preferred email address."""

__metaclass__ = type
__all__ = ['check_script']


def check_script(con, log, hostname, scriptname, completed_from, completed_to):
    """Check whether a script ran on a specific host within stated timeframe.

    Return True on success, or log an error message and return False
    """
    cur = con.cursor()
    cur.execute("""
        SELECT id
        FROM ScriptActivity
        WHERE hostname='%s' AND name='%s'
            AND date_completed BETWEEN '%s' AND '%s'
        """ % (hostname, scriptname, completed_from, completed_to))
    try:
        script_id = cur.fetchone()[0]
        return script_id
    except TypeError:
        try:
            cur.execute("""
                SELECT MAX(date_completed)
                FROM ScriptActivity
                WHERE hostname='%s' AND name='%s'
            """ % (hostname, scriptname))
            date_last_seen = cur.fetchone()[0]
            if not date_last_seen:
                raise
            log.fatal(
                "The script '%s' didn't run on '%s' between "
                "%s and %s (last seen %s)"
                    % (scriptname, hostname, completed_from,
                        completed_to, date_last_seen)
                )
        except:
            log.fatal(
                "The script '%s' didn't run on '%s' between %s and %s"
                    % (scriptname, hostname, completed_from, completed_to)
                )
        return False
