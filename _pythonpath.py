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

env = os.path.join(top, 'env')
stdlib_dir = os.path.join(env, 'lib', 'python%s' % sys.version[:3])

if ('site' in sys.modules and
    not sys.modules['site'].__file__.startswith(
        os.path.join(stdlib_dir, 'site.py'))):
    # We have the wrong site.py, so our paths are not set up correctly.
    # We blow up, with a hopefully helpful error message.
    raise RuntimeError(
        'The wrong site.py is imported (%r imported, %r expected). '
        'Scripts should usually be '
        "started with Launchpad's bin/py, or with a Python invoked with "
        'the -S flag.' % (
        sys.modules['site'].__file__, os.path.join(stdlib_dir, 'site.py')))

# Ensure that the virtualenv's standard library directory is in sys.path;
# activate_this will not put it there.
if stdlib_dir not in sys.path and (stdlib_dir + os.sep) not in sys.path:
    sys.path.insert(0, stdlib_dir)

if not sys.executable.startswith(top + os.sep) or 'site' not in sys.modules:
    # Activate the virtualenv.  Avoid importing lp_sitecustomize here, as
    # activate_this imports site before it's finished setting up sys.path.
    orig_disable_sitecustomize = os.environ.get('LP_DISABLE_SITECUSTOMIZE')
    os.environ['LP_DISABLE_SITECUSTOMIZE'] = '1'
    # This is a bit like env/bin/activate_this.py, but to help namespace
    # packages work properly we change sys.prefix before importing site
    # rather than after.
    sys.real_prefix = sys.prefix
    sys.prefix = env
    os.environ['PATH'] = (
        os.path.join(env, 'bin') + os.pathsep + os.environ.get('PATH', ''))
    site_packages = os.path.join(
        env, 'lib', 'python%s' % sys.version[:3], 'site-packages')
    import site
    site.addsitedir(site_packages)
    if orig_disable_sitecustomize is not None:
        os.environ['LP_DISABLE_SITECUSTOMIZE'] = orig_disable_sitecustomize
    else:
        del os.environ['LP_DISABLE_SITECUSTOMIZE']

# Move all our own directories to the front of the path.
new_sys_path = []
for item in list(sys.path):
    if item == top or item.startswith(top + os.sep):
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

# Initialise the Launchpad environment.
if 'LP_DISABLE_SITECUSTOMIZE' not in os.environ:
    if 'lp_sitecustomize' not in sys.modules:
        import lp_sitecustomize
        lp_sitecustomize.main()
