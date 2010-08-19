# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is the python package that defines the 'canonical' package namespace.

# We currently only translate launchpad specific stuff using the Zope3 i18n
# routines, so this is not needed.
#from zope.i18n.messageid import MessageFactory
#_ = MessageFactory("canonical")

# Filter all deprecation warnings for Zope 3.6, which eminate from
# the zope package.
import warnings
filter_pattern = '.*(Zope 3.6|provide.*global site manager).*'
warnings.filterwarnings(
    'ignore', filter_pattern, category=DeprecationWarning)

# XXX wgrant 2010-03-30 bug=551510:
# Also filter apt_pkg warnings, since Lucid's python-apt has a new API.
warnings.filterwarnings(
    'ignore', '.*apt_pkg.*', category=DeprecationWarning)
