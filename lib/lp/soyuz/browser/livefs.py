# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LiveFSNavigation',
    ]

from lp.services.webapp import Navigation
from lp.soyuz.browser.build import BuildNavigationMixin
from lp.soyuz.interfaces.livefs import ILiveFS


class LiveFSNavigation(Navigation, BuildNavigationMixin):
    usedfor = ILiveFS
