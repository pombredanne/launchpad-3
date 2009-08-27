# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""This is not Psycopg 1."""

class Psycopg1Imported(ImportError):
    pass

raise Psycopg1Imported('Importing Psycopg 1.x is forbidden')
