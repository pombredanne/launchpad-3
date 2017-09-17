# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This file works if the Python has been started with -S, or if bin/py
# has been used.

import imp
import os.path
import sys

# Get path to this file.
if __name__ == '__main__':
    filename = __file__
else:
    # If this is an imported module, we want the location of the .py
    # file, not the .pyc, because the .py file may have been symlinked.
    filename = imp.find_module(__name__)[1]
# Get the full, non-symbolic-link directory for this file.  This is the
# project root.
top = os.path.dirname(os.path.abspath(os.path.realpath(filename)))

site_dir = os.path.join(top, 'parts', 'scripts')

if ('site' in sys.modules and
    not sys.modules['site'].__file__.startswith(
        os.path.join(site_dir, 'site.py'))):
    # We have the wrong site.py, so our paths are not set up correctly.
    # We blow up, with a hopefully helpful error message.
    raise RuntimeError(
        'The wrong site.py is imported (%r imported, %r expected). '
        'Scripts should usually be '
        "started with Launchpad's bin/py, or with a Python invoked with "
        'the -S flag.' % (
        sys.modules['site'].__file__, os.path.join(site_dir, 'site.py')))

if site_dir not in sys.path:
    sys.path.insert(0, site_dir)
elif 'site' not in sys.modules:
    # XXX 2010-05-04 gary bug 575206
    # This one line is to support Mailman 2, which does something unexpected
    # to set up its paths.
    sys.path[:] = [p for p in sys.path if 'site-packages' not in p]
import site  # sets up paths
