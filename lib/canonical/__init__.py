# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# This is the python package that defines the 'canonical' package namespace.

# We currently only translate launchpad specific stuff using the Zope3 i18n
# routines, so this is not needed.
#from zope.i18n.messageid import MessageFactory
#_ = MessageFactory("canonical")

# XXX mars 2008-04-15:
# Filter all deprecation warnings during the transition period to
# Zope 3.4.
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
