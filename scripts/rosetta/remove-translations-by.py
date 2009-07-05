#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

# (Suppressing pylint "relative import" warning 0403 for _pythonpath)

__metaclass__ = type

import _pythonpath

from lp.translations.scripts.remove_translations import RemoveTranslations


if __name__ == '__main__':
    script = RemoveTranslations(
        'canonical.launchpad.scripts.remove-translations',
        dbuser='rosettaadmin')
    script.run()
