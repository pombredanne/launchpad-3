# Copyright 2005 Canonical Ltd.  All rights reserved.

import _pythonpath

import time, sys
from psycopg import ProgrammingError
from sqlobject import SQLObjectNotFound
from datetime import datetime, timedelta
from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor
from canonical.launchpad.database import (POTranslation, POSubmission,
    POSelection, POFile)
from canonical.launchpad.scripts import db_options
from canonical.database.sqlbase import flush_database_updates

def fix_submission(submission, translation):
    """Fix the submission (if needed)."""
    new_text = submission.pomsgset.potmsgset.apply_sanity_fixes(
        translation.translation)

    if new_text == translation.translation:
        # Nothing changed.
        return

    # If we already have the fixed value in our database, we don't need to
    # create it.
    try:
        newtranslation = POTranslation.byTranslation(new_text)
    except SQLObjectNotFound:
        newtranslation = POTranslation(translation=new_text)

    # Store the new value.
    submission.potranslation = newtranslation


def main():
    ztm = initZopeless()
    # We need to use raw queries so every commit will flush the changes done
    # to POTranslation and don't get problems related with excess memory
    # usage.
    total_potranslations = 0
    c = cursor()
    c.execute("SELECT POTranslation.id FROM POTranslation")
    outf = open('/tmp/rosids.out','w')
    while True:
        row = c.fetchone()
        if row is None:
            break
        print >> outf, row[0]
        total_potranslations += 1
    outf.close()
    ids = open('/tmp/rosids.out')
    count = 0
    started = time.time()
    for id in ids:
        id = int(id)
        count += 1
        translation = POTranslation.get(id)
        submissions = POSubmission.selectBy(potranslationID=translation.id)
        for submission in submissions:
            fix_submission(submission, translation)
        if count % 5000 == 0 or count == total_potranslations:
            done = float(count) / total_potranslations
            todo = total_potranslations - count
            now = time.time()
            elapsed = now - started
            eta = timedelta(seconds=(elapsed / done) - elapsed)
            print >> sys.stderr, '%0.4f done (%d of %d). eta %s' % (
                    done*100, count, total_potranslations, eta
                    )
            ztm.commit()
        else:
            flush_database_updates()
    ztm.commit()

    # Now, it's time to remove all empty translations
    try:
        empty_translation = POTranslation.byTranslation('')
    except SQLObjectNotFound:
        return
    submissions = POSubmission.selectBy(potranslationID=empty_translation.id)
    for submission in submissions:
        poselections = POSelection.select(
            "activesubmission=%d OR publishedsubmission=%d" % (
            submission.id, submission.id))
        for poselection in poselections:
            if poselection.activesubmissionID == submission.id:
                poselection.activesubmission = None
            if poselection.publishedsubmissionID == submission.id:
                poselection.publishedsubmission = None
            poselection.sync()

        # Update all POFile.latestsubmission fields:
        pofiles = POFile.select("latestsubmission=%d" % (submission.id))
        for pofile in pofiles:
            results = POSubmission.select('''
                POSubmission.pomsgset = POMsgSet.id AND
                POMsgSet.pofile = %d AND
                POSubmission.id <> %d''' % (pofile.id, submission.id),
                orderBy='-datecreated',
                clauseTables=['POMsgSet'])
            results = list(results)
            if results:
                # We have another submission we can use
                pofile.latestsubmission = results[0]
            else:
                # We have no more submissions
                pofile.latestsubmission = None
        ztm.commit()
        submission.pomsgset.iscomplete = False
        submission.destroySelf()
        ztm.commit()
    POTranslation.delete(empty_translation.id)
    ztm.commit()

if __name__ == '__main__':
    parser = OptionParser()
    db_options(parser)
    (opts, args) = parser.parse_args()
    main()


