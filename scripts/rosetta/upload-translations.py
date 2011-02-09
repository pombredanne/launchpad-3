#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=W0403

"""Upload translations to given package."""

__metaclass__ = type

import _pythonpath

from lp.translations.scripts.upload_translations import (
    UploadPackageTranslations)


if __name__ == '__main__':
    script = UploadPackageTranslations('upload-translations')
    script.run()
