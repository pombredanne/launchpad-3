#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
# (Suppressing pylint "relative import" warning 0403 for _pythonpath)

__metaclass__ = type

import _pythonpath

from canonical.launchpad.scripts.remove_obsolete_translations import (
    RemoveObsoleteTranslations)


if __name__ == '__main__':
    script = RemoveObsoleteTranslations(
        'canonical.launchpad.scripts.remove-obsolete-translations',
        dbuser='rosettaadmin')
    script.run()
