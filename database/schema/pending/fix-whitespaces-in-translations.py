# Copyright 2005 Canonical Ltd.  All rights reserved.

from psycopg import ProgrammingError
from sqlobject import SQLObjectNotFound

from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor
from canonical.launchpad.database import (POTranslation, POSubmission,
    POSelection)

def fix_submission(submission, translation):
    msgid = submission.pomsgset.potmsgset.primemsgid_
    striped_msgid = msgid.msgid.strip()
    striped_translation = translation.translation.strip()
    newtranslation = None
    newvalue = None
    if len(striped_msgid) == 0:
        newvalue = ''
    if len(striped_msgid) != len(msgid.msgid):
        # There are whitespaces that we should copy to the translation
        # after stripping it.
        length = len(msgid.msgid)
        length_prefix = length - len(msgid.msgid.lstrip())
        length_postfix = length - len(msgid.msgid.rstrip())
        prefix = msgid.msgid[:length_prefix]
        if length_postfix == 0:
            postfix = ''
        else:
            postfix = msgid.msgid[-length_postfix:]
        newvalue = '%s%s%s' % (
                prefix, striped_translation, postfix)
        try:
            newtranslation = POTranslation.byTranslation(newvalue)
        except SQLObjectNotFound:
            newtranslation = None
    elif len(striped_translation) != len(translation.translation):
        # The msgid does not have any whitespace, we need to remove
        # the extra ones added to this translation.
        newvalue = striped_translation

    if newvalue == translation.translation:
        return

    if newtranslation is not None:
        submission.potranslation = newtranslation
    elif newvalue is not None:
        translation.translation = newvalue


def main():
    ztm = initZopeless()
    # We need to use raw queries so every commit will flush the changes done
    # to POTranslation and don't get problems related with excess memory
    # usage.
    c = cursor()
    c.execute("SELECT POTranslation.id FROM POTranslation")
    ids = [id for (id,) in c.fetchall()]
    for id in ids:
        translation = POTranslation.get(id)
        submissions = POSubmission.selectBy(potranslationID=translation.id)
        previous_msgid = None
        for submission in submissions:
            # This is a bit tricky as we assume that we will not have the same
            # translation for different msgids.
            # This script will be executed first in staging so we will show a
            # warning only if that's the case, usually, those errors should be
            # fixed by hand as will be related to fuzzy strings.
            current_msgid = submission.pomsgset.potmsgset.primemsgid_.msgid
            if previous_msgid is None:
                previous_msgid = current_msgid
            elif (len(previous_msgid.strip()) > 0 and
                  len(translation.translation.strip()) > 0 and
                  previous_msgid != current_msgid):
                print ('Found two different msgids with the same'
                       ' translation:\n'
                       'msgid1: \'%r\'\n'
                       'msgid2: \'%r\'\n'
                       'translation: \'%r\'\n' % (previous_msgid,
                            current_msgid, translation.translation))
                ztm.abort()
                break

            fix_submission(submission, translation)
            ztm.commit()

    # Now, it's time to remove all empty translations
    empty_translation = POTranslation.byTranslation('')
    submissions = POSubmission.selectBy(potranslationID=empty_translation.id)
    for submission in submissions:
        poselections = POSelection.select(
            "activesubmission=%d OR publishedsubmission=%d" % (
            submission.id, submission.id))
        for poselection in poselections:
            if poselection.activesubmission == submission:
                poselection.activesubmission = None
            if poselection.publishedsubmission == submission:
                poselection.publishedsubmission = None
            poselection.sync()

        submission.pomsgset.iscomplete = False
        POSubmission.delete(submission)
    POTranslation.delete(empty_translation)
    ztm.commit()

if __name__ == '__main__':
    main()


