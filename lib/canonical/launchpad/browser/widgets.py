# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Customized widgets used in Launchpad."""

__metaclass__ = type

__all__ = ['TitleWidget', 'SummaryWidget', 'DescriptionWidget',
           'WhiteboardWidget',
           'ShipItRecipientDisplaynameWidget', 'ShipItOrganizationWidget',
           'ShipItCityWidget', 'ShipItProvinceWidget',
           'ShipItAddressline1Widget', 'ShipItAddressline2Widget',
           'ShipItPhoneWidget', 'ShipItReasonWidget', 'ShipItQuantityWidget']

from zope.interface import implements

from zope.schema.interfaces import IText
from zope.app.form.browser import TextAreaWidget, TextWidget, IntWidget

from canonical.widgets.textwidgets import StrippedTextWidget

class TitleWidget(StrippedTextWidget):
    """A launchpad title widget; a little wider than a normal Textline."""
    displayWidth = 44


class SummaryWidget(TextAreaWidget):
    """A widget to capture a summary."""
    width = 44
    height = 5


class DescriptionWidget(TextAreaWidget):
    """A widget to capture a description."""
    width = 44
    height = 10


class WhiteboardWidget(TextAreaWidget):
    """A widget to capture a whiteboard."""
    width = 44
    height = 5


class ShipItRecipientDisplaynameWidget(TextWidget):
    """See IShipItRecipientDisplayname"""
    displayWidth = displayMaxWidth = 20


class ShipItOrganizationWidget(TextWidget):
    """See IShipItOrganization"""
    displayWidth = displayMaxWidth = 30


class ShipItCityWidget(TextWidget):
    """See IShipItCity"""
    displayWidth = displayMaxWidth = 30


class ShipItProvinceWidget(TextWidget):
    """See IShipItProvince"""
    displayWidth = displayMaxWidth = 30


class ShipItAddressline1Widget(TextWidget):
    """See IShipItAddressline1"""
    displayWidth = displayMaxWidth = 30


class ShipItAddressline2Widget(TextWidget):
    """See IShipItAddressline2"""
    displayWidth = displayMaxWidth = 30


class ShipItPhoneWidget(TextWidget):
    """See IShipItPhone"""
    displayWidth = displayMaxWidth = 16


class ShipItReasonWidget(TextAreaWidget):
    """See IShipItReason"""
    width = 40
    height = 4


class ShipItQuantityWidget(IntWidget):
    """See IShipItQuantity"""
    displayWidth = 4
    displayMaxWidth = 3
    style = 'text-align: right'
