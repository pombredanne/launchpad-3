#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

# Update the type of all Feisty requests since these are the only ones we can
# still infer.

import _pythonpath

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.database import ShippingRequest
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless
from canonical.launchpad.interfaces import (
    ShipItDistroSeries, ShipItFlavour, ShippingRequestType)


execute_zcml_for_scripts()
ztm = initZopeless(implicitBegin=False)

query = """
    ShippingRequest.type IS NULL
    AND ShippingRequest.id IN (
        SELECT request FROM RequestedCDs WHERE distrorelease = %s)
    """ % sqlvalues(ShipItDistroSeries.FEISTY)

while True:
    ztm.begin()
    requests = ShippingRequest.select(query)[:50]
    if requests.count() == 0:
        break
    for request in requests:
        requested_cds = request.getAllRequestedCDs()
        is_custom = False
        for flavour in ShipItFlavour.items:
            if request.containsCustomQuantitiesOfFlavour(flavour):
                is_custom = True
        if is_custom:
            request.type = ShippingRequestType.CUSTOM
            print "Updated type of request #%d to CUSTOM" % request.id
        else:
            request.type = ShippingRequestType.STANDARD
            print "Updated type of request #%d to STANDARD" % request.id

    ztm.commit()
