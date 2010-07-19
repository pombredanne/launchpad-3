#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

import _pythonpath

from canonical.config import config
from lp.translations.scripts.po_import import TranslationsImport

if __name__ == '__main__':
    script = TranslationsImport(
        'rosetta-poimport', dbuser=config.poimport.dbuser)
    script.lock_and_run()
