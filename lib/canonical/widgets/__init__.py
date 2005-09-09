"""Canonical widgets.

These may be fed back into Zope3 at some point.

"""
from date import IDateWidget, DateWidget
from owner import IUserWidget, HiddenUserWidget
from popup import ISinglePopupWidget, SinglePopupWidget
from context import IContextWidget, ContextWidget
from password import PasswordChangeWidget
