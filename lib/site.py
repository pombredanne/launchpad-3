# LAUNCHPAD HACK OF STDLIB SITE.PY
# Why are we hacking site.py?
# The short answer is that namespace packages in setuptools have problems.
# A longer answer is that we have to import pkg_resources before namespace
# package .pth files are processed or else the distribution's namespace
# packages will mask all of the egg-based packages in the same namespace
# package.  Normally, we handle that in bin/py or _pythonpath. but sometimes
# we do subprocess calls, relying on the PYTHONPATH to set the eggs
# correctly.  It is for this situation that we have hacked site.py.

# Before we actually import pkg_resources, we need to filter warnings,
# because importing pkg_resources will otherwise trigger a type of
# warnings that we don't care about.  These warnings occur when Python
# 2.5 and higher encounters directories that do not have an __init__.py.
# These can be data directories, or namespace directories in
# site-packages, such as "zope" or "lazr."
__import__('warnings').filterwarnings(
    'ignore', "Not importing directory '.+': missing __init__.py")

# Now here is the important part:
try:
    __import__('pkg_resources') # Use __import__ to not pollute the namespace.
except ImportError:
    pass

# Now, we want to get the usual site.py behavior.
import os
import sys
execfile(
    os.path.join(sys.prefix, 'lib', 'python' + sys.version[:3], 'site.py'))

# Perform other start-up initialization.
from lp.services.mime import customizeMimetypes
customizeMimetypes()
