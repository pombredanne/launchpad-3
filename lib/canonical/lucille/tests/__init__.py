# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 28075773-73fd-4699-82ed-610df135d2a5

import os

here = os.path.dirname(os.path.realpath(__file__))

def datadir(path):
    """Returns the given relative to the datadirectory as a
    fully-qualified path.
    """
    if path.startswith("/"):
        raise ValueError("Path is not relative: %s" % path)
    return os.path.join(here, 'data', path)

