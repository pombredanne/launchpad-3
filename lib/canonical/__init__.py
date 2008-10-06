# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# This is the python package that defines the 'canonical' package namespace.

# We currently only translate launchpad specific stuff using the Zope3 i18n
# routines, so this is not needed.
#from zope.i18n.messageid import MessageFactory
#_ = MessageFactory("canonical")

# XXX sinzui 2008-10-03:
# Filter all deprecation warnings for Zope 3.6, which eminate from
# the zope package.
import warnings
warnings.filterwarnings(
    'ignore',
    ".*(Zope 3.6|Use register).*",
    category=DeprecationWarning)
