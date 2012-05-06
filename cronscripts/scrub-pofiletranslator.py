#!/usr/bin/python -S
#
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Update `POFileTranslator` table."""

import _pythonpath

from lp.translations.scripts.scrub_pofiletranslator import (
    ScrubPOFileTranslator,
    )


__metaclass__ = type


if __name__ == '__main__':
    script = ScrubPOFileTranslator(
        'scrub-pofiletranslator', 'scrub_pofiletranslator')
    script.lock_and_run()
