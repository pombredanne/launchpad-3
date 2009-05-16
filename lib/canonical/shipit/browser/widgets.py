# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Customized widgets used in Shipit."""

__metaclass__ = type

__all__ = [
    'ShipItAddressline1Widget',
    'ShipItAddressline2Widget',
    'ShipItCityWidget',
    'ShipItOrganizationWidget',
    'ShipItPhoneWidget',
    'ShipItProvinceWidget',
    'ShipItQuantityWidget',
    'ShipItReasonWidget',
    'ShipItRecipientDisplaynameWidget',
    ]


from zope.app.form.browser import TextAreaWidget, TextWidget, IntWidget


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
