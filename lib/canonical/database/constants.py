# Copyright 2004 Canonical Ltd
#

class NowUTC(object):
    def __sqlrepr__(self, dbName):
        return "CURRENT_TIMESTAMP AT TIME ZONE 'UTC'"
UTC_NOW = NowUTC() # All upper because this is the constants module
nowUTC = UTC_NOW

class Default(object):
    def __sqlrepr__(self, dbName):
        return "DEFAULT"
DEFAULT = Default()

