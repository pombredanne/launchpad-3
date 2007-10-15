#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

# A script to create OpenIDRPConfigs for trust roots we care about.
# This is essentially porting the values from the KNOWN_TRUST_ROOTS
# dict that we care about.

import _pythonpath

import os

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    ILibraryFileAliasSet, IOpenIDRPConfigSet)
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless
from canonical.launchpad.interfaces import PersonCreationRationale as PCR

execute_zcml_for_scripts()
ztm = initZopeless()

# Create Canonical logo file in Librarian
filename = os.path.join(
    config.root, 'lib/canonical/launchpad/icing/canonical-logo.png')
size = os.path.getsize(filename)
fp = open(filename, 'rb')
logo = getUtility(ILibraryFileAliasSet).create(
    name='canonical-logo.png', size=size, file=fp, contentType='image/png')

# Create RP configs
for trust_root in ['http://pdl-dev.co.uk', 'http://www.mmania.biz',
                   'http://shop.canonical.com', 'https://shop.canonical.com',
                   'https://testshop.canonical.com']:
    rpconfig = getUtility(IOpenIDRPConfigSet).new(
        trust_root=trust_root,
        displayname="The Ubuntu Store from Canonical",
        description=("For the Ubuntu Store, you need a Launchpad account "
                     "so we can remember your order details and keep in "
                     "touch with you about your orders."),
        logo=logo,
        allowed_sreg=['email', 'fullname', 'nickname',
                      'x_address1', 'x_address2', 'x_organization',
                      'x_city', 'x_province', 'country', 'postcode',
                      'x_phone'],
        creation_rationale=PCR.OWNER_CREATED_UBUNTU_SHOP)

ztm.commit()
