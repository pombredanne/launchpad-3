# Copyright 2005 Canonical Ltd.  All rights reserved.

from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor
from canonical.launchpad.database import POMsgSet

def main():
    ztm = initZopeless()
    # We need to use raw queries so every commit will flush the changes done
    # to POMsgSet and don't get problems related with excessive memory usage.
    c = cursor()
    c.execute("SELECT POMsgSet.id FROM POMsgSet")
    ids = [id for (id,) in c.fetchall()]
    for id in ids:
        pomsgset = POMsgSet.get(id)
        # Now is time to check if the fuzzy flag should be copied to
        # the web flag
        matches = 0
        for pluralform in range(pomsgset.pluralforms):
            if (pomsgset.activeSubmission(pluralform) ==
                pomsgset.publishedSubmission(pluralform)):
                matches += 1
        if matches == pomsgset.pluralforms:
            # The active submission is exactly the same as the
            # published one, so the fuzzy and complete flags should be
            # also the same.
            print 'changed!'
            pomsgset.isfuzzy = pomsgset.publishedfuzzy
            pomsgset.iscomplete = pomsgset.publishedcomplete

        ztm.commit()

if __name__ == '__main__':
    main()
