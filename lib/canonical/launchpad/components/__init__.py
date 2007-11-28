# Copyright 2006 Canonical Ltd.  All rights reserved.

"""
> What is this package for? Is it a dumping ground for anything that doesn't
> > fit in canonical.launchpad.database or canonical.launchpad.browser? Or does
> > it actually have a defined purpose that just hasn't been documented in the
> > __init__.py ?

Way back in the day, Mark had the idea to split the various parts of
Launchpad software up according to the type of thing the code represents
in software.  So, one place for all interfaces, one place for all
database classes, one place for all templates...

"Components" is a place for adapters and utilities, and all the things
in it should be "black box" and looked up only via their zcml registrations.

I don't think the distinction of "components" is currently useful.  So,
it should be removed, and its contents distributed to better places in
the code.
"""

from canonical.launchpad.components.objectdelta import ObjectDelta
