# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Update the interface schema values due to circular imports.

There are situations where there would normally be circular imports to define
the necessary schema values in some interface fields.  To avoid this the
schema is initially set to `Interface`, but this needs to be updated once the
types are defined.
"""

__metaclass__ = type


from canonical.launchpad.interfaces.branch import IBranch
from canonical.launchpad.interfaces.product import IProduct


IBranch['product'].schema = IProduct
