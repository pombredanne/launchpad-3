# Copyright 2004 Canonical Ltd
#
# arch-tag: 10b21ab8-0009-4efd-af07-ba17c593c752

class NowUTC(object):
    def __sqlrepr__(self, dbName):
        return "CURRENT_TIMESTAMP AT TIME ZONE 'UTC'"
UTCNOW = NowUTC() # All upper because this is the constants module
nowUTC = UTC_NOW

class Default(object):
    def __sqlrepr__(self, dbName):
        return "DEFAULT"
DEFAULT = Default()

