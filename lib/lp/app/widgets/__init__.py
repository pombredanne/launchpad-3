# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0401

"""Canonical widgets.

These may be fed back into Zope3 at some point.
"""

from lp.app.widgets.announcementdate import (
    IAnnouncementDateWidget, AnnouncementDateWidget)
from lp.app.widgets.context import IContextWidget, ContextWidget
from lp.app.widgets.date import (
    DateWidget, DateTimeWidget, DatetimeDisplayWidget)
from lp.app.widgets.image import (
    GotchiTiedWithHeadingWidget, ImageChangeWidget)
from lp.app.widgets.itemswidgets import *
from lp.app.widgets.location import LocationWidget
from lp.app.widgets.owner import IUserWidget, HiddenUserWidget
from lp.app.widgets.password import PasswordChangeWidget
from lp.app.widgets.textwidgets import (
    DelimitedListWidget, LocalDateTimeWidget, LowerCaseTextWidget,
    StrippedTextWidget, TokensTextWidget, URIWidget)
