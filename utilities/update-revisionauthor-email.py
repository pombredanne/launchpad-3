#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Try to link RevionAuthors to Launchpad Person entries.

Iterate through the RevisionAuthors and extract their email address.
Then use that email address to link to a Person.
"""

import _pythonpath

import email.Utils
import sys

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless

from canonical.launchpad.database.revision import RevisionAuthor

def main(argv):
    execute_zcml_for_scripts()
    ztm = initZopeless()
    try:
        for author in RevisionAuthor.select():
            if author.email is None:
                email_address = email.Utils.parseaddr(author.name)[1]
                # If there is no @, then it isn't a real email address.
                if '@' in email_address:
                    author.email = email_address
                    if author.linkToLaunchpadPerson():
                        print "%s linked to %s" % (
                            author.name, author.person.displayname)
        ztm.commit()
    finally:
        ztm.abort()
    print "Done."


if __name__ == '__main__':
    main(sys.argv)
