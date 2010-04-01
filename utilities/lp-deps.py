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
JS_DIRS = ['lib/lp/code/javascript']

for DIR in JS_DIRS:
    full_dir = os.path.join(TOP, DIR)
    for filename in os.listdir(full_dir):
        if filename.endswith('.js'):
            absolute_filename = os.path.join(full_dir, filename)
            print absolute_filename
    #TODO: Add symlink to icing build dir
