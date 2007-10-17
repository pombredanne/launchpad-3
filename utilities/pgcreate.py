#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Create a database

Like createdb, except will retry on failure.
."""

__metaclass__ = type

import sys
import time
import psycopg

def main():
    if len(sys.argv) != 3:
        print >> sys.stderr, 'Usage: %s [template] [dbname]' % sys.argv[0]
        return 1

    template, dbname = sys.argv[1:]

    con = psycopg.connect('dbname=template1')
    con.set_isolation_level(0)
    for attempt in range(0, 10):
        try:
            cur = con.cursor()
            cur.execute(
                    "CREATE DATABASE %s TEMPLATE = %s ENCODING = 'UTF8'" % (
                        dbname, template
                        )
                    )
        except psycopg.Error:
            if attempt == 9:
                raise
            time.sleep(1)
        else:
            return 0
    return 1

if __name__ == '__main__':
    sys.exit(main())
