# Copyright 2008 Canonical Ltd.  All rights reserved.

"""This is not Psycopg 1."""

class Psycopg1Imported(ImportError):
    pass

raise Psycopg1Imported('Importing Psycopg 1.x is forbidden')
