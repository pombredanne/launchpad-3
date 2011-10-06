# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This deprecation causes a load of spurious DeprecationWarnings.
# Hopefully this decision will be reversed before 3.3 is released causing
# this to become a load of spurious exceptions. Bug 39883.
import warnings


warnings.filterwarnings(
        'ignore', r'.*Use explicit i18n:translate=""', DeprecationWarning
        )

# Modules should 'from canonical.launchpad import _' instead of constructing
# their own MessageFactory
from zope.i18nmessageid import MessageFactory
_ = MessageFactory("launchpad")
