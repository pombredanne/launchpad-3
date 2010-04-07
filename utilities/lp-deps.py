#!/usr/bin/python
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Print the Launchpad javascript files we are using.

The output of this script is meant to be given to the jsbuild script so that
they are included in the launchpad.js file.
"""

__metaclass__ = type

import os
import sys

TOP = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
# JS_DIRSET is a tuple of the dir where the code exists, and the name of the
# symlink it should be linked as in the icing build directory.
JS_DIRSET = [
    (os.path.join('lib', 'lp', 'code', 'javascript'), 'code'),]
ICING_ROOT = os.path.join(TOP, 'lib', 'canonical', 'launchpad', 'icing')
ICING_BUILD = os.path.join(ICING_ROOT, 'build')

for DIRSET in JS_DIRSET:
    full_dir = os.path.join(TOP, DIRSET[0])
    # We don't want the tests to be included.  If we want to nest the files in
    # more folders though, this is where we change it.
    for filename in os.listdir(full_dir):
        if filename.endswith('.js'):
            absolute_filename = os.path.join(full_dir, filename)
            print absolute_filename

    os.symlink(full_dir, os.path.join(ICING_BUILD, DIRSET[1]))
