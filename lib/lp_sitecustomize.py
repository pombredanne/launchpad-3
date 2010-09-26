# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This file is imported by parts/scripts/sitecustomize.py, as set up in our
# buildout.cfg (see the "initialization" key in the "[scripts]" section).

import os
import warnings
import logging

from bzrlib.branch import Branch
from lp.services.log.loglevels import *
from lp.services.log.mappingfilter import MappingFilter
from lp.services.log.nullhandler import NullHandler
from lp.services.mime import customizeMimetypes
from zope.security import checker


def add_custom_loglevels():
    """Add out custom log levels to the Python logging package."""
    logging.addLevelName(DEBUG2, 'DEBUG2')
    logging.addLevelName(DEBUG3, 'DEBUG3')
    logging.addLevelName(DEBUG4, 'DEBUG4')
    logging.addLevelName(DEBUG5, 'DEBUG5')
    logging.addLevelName(DEBUG6, 'DEBUG6')
    logging.addLevelName(DEBUG7, 'DEBUG7')
    logging.addLevelName(DEBUG8, 'DEBUG8')
    logging.addLevelName(DEBUG9, 'DEBUG9')

def silence_bzr_logger():
    """Install the NullHandler on the bzr logger to silence logs."""
    logging.getLogger('bzr').addHandler(NullHandler())

def silence_zcml_logger():
    """Lower level of ZCML parsing DEBUG messages."""
    config_filter = MappingFilter(
        {logging.DEBUG: (7, 'DEBUG4')}, 'config')
    logging.getLogger('config').addFilter(config_filter)

def silence_transaction_logger():
    """Lower level of DEBUG messages from the transaction module."""
    # Transaction logging is too noisy. Lower its DEBUG messages
    # to DEBUG3. Transactions log to loggers named txn.<thread_id>,
    # so we need to register a null handler with a filter to ensure
    # the logging records get mutated before being propagated up
    # to higher level loggers.
    txn_handler = NullHandler()
    txn_filter = MappingFilter(
        {logging.DEBUG: (8, 'DEBUG3')}, 'txn')
    txn_handler.addFilter(txn_filter)
    logging.getLogger('txn').addHandler(txn_handler)

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
    add_custom_loglevels()
    customizeMimetypes()
    dont_wrap_class_and_subclasses(Branch)
    silence_warnings()
    silence_bzr_logger()
    silence_zcml_logger()
    silence_transaction_logger()

main()
