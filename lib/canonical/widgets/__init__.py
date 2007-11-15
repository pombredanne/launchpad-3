"""Canonical widgets.

These may be fed back into Zope3 at some point.

"""
from date import IDateWidget, DateWidget, DatetimeDisplayWidget
from image import GotchiTiedWithHeadingWidget, ImageChangeWidget
from owner import IUserWidget, HiddenUserWidget
from popup import (
    ISinglePopupWidget, SearchForUpstreamPopupWidget, SinglePopupWidget)
from context import IContextWidget, ContextWidget
from itemswidgets import *
from password import PasswordChangeWidget
from textwidgets import (
    LocalDateTimeWidget, LowerCaseTextWidget, StrippedTextWidget, URIWidget)
