# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

__all__ = ['main']

import paramiko

#############################################################################
# Try to guide users past support problems we've encountered before
if not paramiko.__version__.startswith('1.7.4'):
    raise RuntimeError('Your version of paramiko (%s) is not supported.  '
                       'Please use 1.7.4.' % (paramiko.__version__,))
# maybe add similar check for bzrlib?
# End
#############################################################################

from devscripts.ec2test.commandline import main
main # shut up pyflakes
