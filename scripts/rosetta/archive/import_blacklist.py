#!/usr/bin/python2.4 -w

import sys

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.database import Language

def import_blacklist(codes):
    for code in codes:
        try:
            language = Language.selectBy(code = code)[0]
        except IndexError:
            raise RuntimeError("No language with the code '%s'." % code)

        language.translatable = False

if __name__ == '__main__':
    tm = initZopeless()

    codes = []

    for line in sys.stdin:
        codes.append(line.strip())

    import_blacklist(codes)

    tm.commit()

