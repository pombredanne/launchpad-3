# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# Modules should 'from canonical.launchpad import _' instead of constructing
# their own MessageIDFactory
from zope.i18nmessageid import MessageFactory
_ = MessageFactory("launchpad")

