# Copyright 2004 Canonical Ltd
#
# arch-tag: 10b21ab8-0009-4efd-af07-ba17c593c752

class NowUTC:
    def __sqlrepr__(self, dbName):
        return "CURRENT_TIMESTAMP AT TIME ZONE 'UTC'"

nowUTC = NowUTC()
