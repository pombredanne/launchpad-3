# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This file is imported by parts/scripts/sitecustomize.py, as set up in our
# buildout.cfg (see the "initialization" key in the "[scripts]" section).

import os
import warnings
import logging

from bzrlib.branch import Branch
from lp.services.log.nullhandler import NullHandler
from lp.services.mime import customizeMimetypes
from zope.security import checker


def silence_root_logger():
    """Install the NullHandler on the root logger to silence logs."""
    logging.getLogger('bzr').addHandler(NullHandler())

def dont_wrap_class_and_subclasses(cls):
    checker.BasicTypes.update({cls: checker.NoProxy})
    for subcls in cls.__subclasses__():
        dont_wrap_class_and_subclasses(subcls)

def silence_warnings():
    """Silence warnings across the entire Launchpad project."""
    # pycrypto-2.0.1 on Python2.6:
    #   DeprecationWarning: the sha module is deprecated; use the hashlib
    #   module instead
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="Crypto")

def main():
    # Note that we configure the LPCONFIG environmental variable in the
    # custom buildout-generated sitecustomize.py in
    # parts/scripts/sitecustomize.py rather than here.  This is because
    # the instance name, ${configuration:instance_name}, is dynamic,
    # sent to buildout from the Makefile.  See buildout.cfg in the
    # initialization value of the [scripts] section for the code that
    # goes into this custom sitecustomize.py.  We do as much other
    # initialization as possible here, in a more visible place.
    os.environ['STORM_CEXTENSIONS'] = '1'
    customizeMimetypes()
    dont_wrap_class_and_subclasses(Branch)
    silence_warnings()
    silence_root_logger()

main()
