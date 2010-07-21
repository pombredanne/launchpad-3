# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['FeatureSettings'
    'FeatureSettingsFromDatabase',
    ]

__metaclass__ = type


from storm.locals import Store


from lp.services.database import collection
from lp.services.features.model import FeatureFlag


# TODO: might be nice to have features set only in memory for easier testing,
# but so much other code needs the db we don't bother for now


class FeatureSettings(object):
    """Abstract base class for definitons of feature settings.
    
    These typically come from the FeatureFlag database table, but might 
    be overridden for various reasons."""

    def getSettings(self):
        """Returns all settings. 
        
        List of [(flag_name, scope_name, priority, value_name)]
        """
