# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes that manage FeatureFlagChange changes."""

__all__ = [
    'ChangeLog',
    ]

__metaclass__ = type

from storm.locals import Desc

from lp.services.features.model import (
    FeatureFlagChange,
    getFeatureStore,
    )


class ChangeLog:
    """A log of `FeatureFlagChange` changes."""

    @staticmethod
    def get():
        """return a result set of `FeatureFlagChange` changes."""
        store = getFeatureStore()
        rs = store.find(FeatureFlagChange)
        rs.order_by(Desc(FeatureFlagChange.date_changed))
        return rs

    @staticmethod
    def append(diff):
        """Append a diff to the FeatureFlagChange changes."""
        store = getFeatureStore()
        feature_flag_change = FeatureFlagChange(diff)
        store.add(feature_flag_change)
        return feature_flag_change
