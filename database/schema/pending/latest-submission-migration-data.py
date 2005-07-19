# Copyright 2005 Canonical Ltd.  All rights reserved.

from psycopg import ProgrammingError
from sqlobject import SQLObjectNotFound

from canonical.lp import initZopeless
from canonical.launchpad.database import (POFile, POSubmission)

def getLatestSubmission(pofile):
    results = POSubmission.select('''
        POSubmission.pomsgset = POMsgSet.id AND
        POMsgSet.pofile = %d''' % pofile.id,
        orderBy='-datecreated',
        clauseTables=['POMsgSet'])
    try:
        return results[0]
    except IndexError:
        return None

def main():
    ztm = initZopeless()
    pofiles = POFile.select()
    for pofile in pofiles:
        latest_submission = getLatestSubmission(pofile)
        pofile.latestsubmission = latest_submission
        pofile.sync()
        ztm.commit()

if __name__ == '__main__':
    main()


