#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403
# (Suppressing pylint "relative import" warning 0403 for _pythonpath)

__metaclass__ = type

import _pythonpath

from lp.translations.scripts.remove_obsolete_translations import (
    RemoveObsoleteTranslations)


if __name__ == '__main__':
    script = RemoveObsoleteTranslations(
        'canonical.launchpad.scripts.remove-obsolete-translations',
        dbuser='rosettaadmin')
    script.run()
