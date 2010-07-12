# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run the Launchpad tests in Amazon's Elastic Compute Cloud (EC2)."""

__metaclass__ = type

__all__ = []

from bzrlib.plugin import load_plugins
load_plugins()
import paramiko

#############################################################################
# Try to guide users past support problems we've encountered before
if not paramiko.__version__.startswith('1.7.4'):
    raise RuntimeError('Your version of paramiko (%s) is not supported.  '
                       'Please use 1.7.4.' % (paramiko.__version__,))
# maybe add similar check for bzrlib?
# End
#############################################################################

import warnings
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module="boto")
