# LAUNCHPAD HACK OF STDLIB SITE.PY
# Why are we hacking site.py?
# The short answer is that namespace packages in setuptools have problems.
# A longer answer is that we have to import pkg_resources before namespace
# package .pth files are processed or else the distribution's namespace
# packages will mask all of the egg-based packages in the same namespace
# package.  Normally, we handle that in bin/py or _pythonpath. but sometimes
# we do subprocess calls, relying on the PYTHONPATH to set the eggs
# correctly.  It is for this situation that we have hacked site.py.  Here
# is the important part:
try:
    __import__('pkg_resources') # Use __import__ to not pollute the namespace.
except ImportError:
    pass

# Now, we want to get the usual site.py behavior.
import os
import sys
execfile(
    os.path.join(sys.prefix, 'lib', 'python' + sys.version[:3], 'site.py'))
