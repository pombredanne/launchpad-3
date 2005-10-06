# Copyright 2005 Canonical Ltd.  All rights reserved.

from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor
from canonical.launchpad.database import POMsgSet
from canonical.launchpad.scripts import db_options

from optparse import OptionParser
import time
from datetime import datetime,timedelta

def main():
    ztm = initZopeless()
    # We need to use raw queries so every commit will flush the changes done
    # to POMsgSet and don't get problems related with excessive memory usage.
    c = cursor()
    c.execute("SELECT POMsgSet.id FROM POMsgSet order by id desc")
    outf = open('/tmp/rosetta.ids','w')
    total_pomsgsets = 0
    while 1:
        row = c.fetchone()
        if row is None:
            break
        print >> outf, row[0]
	total_pomsgsets += 1
    outf.close()
    inf = open('/tmp/rosetta.ids')

    count = 0
    updated = 0
    started = time.time()

    for id in inf:
	id = int(id)
        pomsgset = POMsgSet.get(id)
        # Now is time to check if the fuzzy flag should be copied to
        # the web flag
        matches = 0
        for pluralform in range(pomsgset.pluralforms):
            if (pomsgset.activeSubmission(pluralform) ==
                pomsgset.publishedSubmission(pluralform)):
                matches += 1
        if matches == pomsgset.pluralforms and (pomsgset.isfuzzy != pomsgset.publishedfuzzy or pomsgset.iscomplete != pomsgset.publishedcomplete):
            # The active submission is exactly the same as the
            # published one, so the fuzzy and complete flags should be
            # also the same.
            pomsgset.isfuzzy = pomsgset.publishedfuzzy
            pomsgset.iscomplete = pomsgset.publishedcomplete
            updated += 1
	count += 1
	if count % 5000 == 0 or count == total_pomsgsets:
            done = float(count) / total_pomsgsets
            todo = total_pomsgsets - count
            now = time.time()
            elapsed = now - started
            eta = timedelta(seconds=(elapsed / done) - elapsed)
            print '\n%0.4f%% processed. %d to go. %d updated. eta %s' % (
                done*100, todo, updated, eta
                )
            ztm.commit()
    ztm.commit()

if __name__ == '__main__':
    parser = OptionParser()
    db_options(parser)
    (options, args) = parser.parse_args()
    main()
