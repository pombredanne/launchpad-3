# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""This package contains the Launchpad.net web application.

It contains the code and templates that glue all the other components
together. As such, it can import from any modules, but nothing should import
from it.
"""

__metaclass__ = type
__all__ = []

# Zope recently changed the behavior of items widgets with regards to missing
# values, but they kindly left this global variable for you to monkey patch if
# you want the old behavior, just like we do.
from zope.app.form.browser import itemswidgets
itemswidgets.EXPLICIT_EMPTY_SELECTION = False

