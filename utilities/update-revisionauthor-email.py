#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Disable pylint complaining about relative import of _pythonpath
# pylint: disable-msg=W0403

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
        total = RevisionAuthor.select().count()
        for number, author in enumerate(RevisionAuthor.select()):
            if author.email is None:
                email_address = email.Utils.parseaddr(author.name)[1]
                # If there is no @, then it isn't a real email address.
                if '@' in email_address:
                    author.email = email_address
                    if author.linkToLaunchpadPerson():
                        print "%s linked to %s" % (
                            author.name.encode('ascii', 'replace'),
                            author.person.name)
        ztm.commit()
    finally:
        ztm.abort()


if __name__ == '__main__':
    main(sys.argv)
