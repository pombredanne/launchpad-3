#! /usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Print a list of directories that contain a valid intltool structure."""

import _pythonpath

from lp.translations.pottery.detect_intltool import find_intltool_dirs


if __name__ == "__main__":
    print "\n".join(find_intltool_dirs())
