# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.services.worlddata.interfaces.country import ICountrySet

from canonical.launchpad.webapp import GetitemNavigation


class CountrySetNavigation(GetitemNavigation):
    usedfor = ICountrySet
