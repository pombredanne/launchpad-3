#!/usr/bin/python

# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Print the YUI modules we are using.

It looks into the main-template.pt file for the yui modules included. It
prints the path to the minified version of these modules.

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
    TOP, 'lib', 'canonical', 'launchpad', 'templates', 'main-template.pt')

YUI_ROOT_RE = re.compile('yui string:\${icingroot}/(.*);')
YUI_MOD_RE = re.compile('\${yui}/(.*?)\.js')

# We need to include some YUI2 js files for the moment too until we
# have a YUI3 datepicker.
YUI2_ROOT_RE = re.compile('yui2 string:\${icingroot}/(.*);')
YUI2_MOD_RE = re.compile('\${yui2}/(.*?)\.js')

def check_for_yui_root(line, yui_root_re):
    match = yui_root_re.search(line)
    if not match:
        return None

    yui_root = os.path.join(ICING_ROOT, match.group(1))
    if not os.path.isdir(yui_root):
        sys.stderr.write(
            "The found YUI root isn't valid: %s\n" % yui_root)
        sys.exit(1)

    return yui_root

yui_root = None
yui2_root = None
template = open(MAIN_TEMPLATE, 'r')
for line in template:
    if yui_root is None:
        yui_root = check_for_yui_root(line, YUI_ROOT_RE)

    if yui2_root is None:
        yui2_root = check_for_yui_root(line, YUI2_ROOT_RE)

    # If either of the yui or yui2 root directories are not yet known
    # then just keep looking for them.
    if yui_root is None or yui2_root is None:
        continue
    else:
        match = YUI_MOD_RE.search(line)
        if match is not None:
            # We want to bundle the minimized version
            module = os.path.join(yui_root, match.group(1)) + '-min.js'
        else:
            match = YUI2_MOD_RE.search(line)
            if match is not None:
                module = os.path.join(yui2_root, match.group(1)) + '-min.js'
            else:
                continue

        if not os.path.isfile(module):
            sys.stderr.write(
                "Found invalid YUI module: %s\n" % module)
        else:
            print module
