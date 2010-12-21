#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Print the YUI modules we are using.

It looks into the base-layout-macros.pt file for the yui modules included.
It prints the path to the minified version of these modules.

The output of this script is meant to be given to the lazr-js build.py script
so that they are included in the launchpad.js file.
"""


__metaclass__ = type

import os
import re
import sys

TOP = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..'))
ICING_ROOT = os.path.join(TOP, 'lib', 'canonical', 'launchpad', 'icing')
MAIN_TEMPLATE = os.path.join(
    TOP, 'lib', 'lp', 'app', 'templates', 'base-layout-macros.pt')

YUI_ROOT_RE = re.compile('yui string:\${icingroot}/(.*);')
YUI_MOD_RE = re.compile('\${yui}/(.*?)\.js')


yui_root = None
template = open(MAIN_TEMPLATE, 'r')
for line in template:
    if yui_root is None:
        match = YUI_ROOT_RE.search(line)
        if not match:
            continue

        yui_root = os.path.join(ICING_ROOT, match.group(1))
        if not os.path.isdir(yui_root):
            sys.stderr.write(
                "The found YUI root isn't valid: %s\n" % yui_root)
            sys.exit(1)
    else:
        match = YUI_MOD_RE.search(line)
        if not match:
            continue
        # We want to bundle the minimized version
        # unless it's a lang module.
        file_path = match.group(1)
        if 'lang' in file_path:
            module = os.path.join(yui_root, match.group(1)) + '.js'
        else:
            module = os.path.join(yui_root, match.group(1)) + '-min.js'
        if not os.path.isfile(module):
            sys.stderr.write(
                "Found invalid YUI module: %s\n" % module)
        else:
            print module
