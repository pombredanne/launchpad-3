#! /usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Print a list of directories that contain a valid intltool structure."""

import _pythonpath


from lp.translations.pottery.detect_intltool import (
    find_intltool_dirs, get_translation_domain)


if __name__ == "__main__":
    for dirname in find_intltool_dirs():
        translation_domain = get_translation_domain(dirname) or "<unknown>"
        print "%s (%s)" % (dirname, translation_domain)
