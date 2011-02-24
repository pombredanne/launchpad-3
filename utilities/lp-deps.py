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

from lazr.js.build import Builder

TOP = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
# JS_DIRSET is a tuple of the dir where the code exists, and the name of the
# symlink it should be linked as in the icing build directory.
JS_DIRSET = [
    (os.path.join('lib', 'lp', 'app', 'javascript'), 'app'),
    (os.path.join('lib', 'lp', 'bugs', 'javascript'), 'bugs'),
    (os.path.join('lib', 'lp', 'code', 'javascript'), 'code'),
    (os.path.join('lib', 'lp', 'registry', 'javascript'), 'registry'),
    (os.path.join('lib', 'lp', 'translations', 'javascript'), 'translations'),
    (os.path.join('lib', 'lp', 'soyuz', 'javascript'), 'soyuz'),
    (os.path.join('lib', 'lp', 'contrib', 'javascript', 'yui3-gallery', 'gallery-accordion'), 'contrib'),
    ]
ICING_ROOT = os.path.join(TOP, 'lib', 'canonical', 'launchpad', 'icing')
ICING_BUILD = os.path.join(ICING_ROOT, 'build')

# Builder has lots of logging, which might not
# play well with printing filenames.  Monkey patch
# to disable it.
def log_none(msg):
    return

for DIRSET in JS_DIRSET:
    full_dir = os.path.join(TOP, DIRSET[0])
    module_name = DIRSET[1]
    BUILD_DIR = os.path.join(ICING_BUILD, module_name)
    if not os.path.exists(BUILD_DIR):
        os.mkdir(BUILD_DIR)
    builder = Builder(
        name=module_name, src_dir=full_dir, build_dir=ICING_BUILD)
    builder.log = log_none
    # We don't want the tests to be included.  If we want to nest the files in
    # more folders though, this is where we change it.
    for filename in os.listdir(full_dir):
        # Some third-party JavaScript libraries may include pre-built -min and
        # -debug files.  Skip those.
        if filename.endswith('-min.js') or filename.endswith('-debug.js'):
            continue
        if filename.endswith('.js'):
            basename, nothing = filename.split('.js')
            min_filename = basename + '-min.js'
            absolute_filename = os.path.join(full_dir, filename)
            builder.link_and_minify(builder.name, absolute_filename)
            print os.path.join(BUILD_DIR, min_filename)
