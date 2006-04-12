# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# This deprecation causes a load of spurious DeprecationWarnings.
# Hopefully this decision will be reversed before 3.3 is released causing
# this to become a load of spurious exceptions.
# XXX: Open a bug on this, citing
# http://mail.zope.org/pipermail/zope3-dev/2005-May/014424.html
# and http://mail.zope.org/pipermail/zope3-dev/2005-December/016781.html
# (the latter apparently discussing undeprecating this)
import warnings
warnings.filterwarnings(
        'ignore', r'.*Use explicit i18n:translate=""', DeprecationWarning
        )

# Modules should 'from canonical.launchpad import _' instead of constructing
# their own MessageFactory
from zope.i18nmessageid import MessageFactory
_ = MessageFactory("launchpad")

