# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0401,W0403

"""Canonical widgets.

These may be fed back into Zope3 at some point.

"""
from date import IDateWidget, DateWidget, DatetimeDisplayWidget
from image import GotchiTiedWithHeadingWidget, ImageChangeWidget
from owner import IUserWidget, HiddenUserWidget
from popup import ISinglePopupWidget, SinglePopupWidget
from context import IContextWidget, ContextWidget
from itemswidgets import *
from password import PasswordChangeWidget
