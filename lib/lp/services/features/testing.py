# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for writing tests that use feature flags."""

__metaclass__ = type
__all__ = ['active_features']


from contextlib import contextmanager
from fixtures import Fixture
from lp.services.features import per_thread
from lp.services.features.flags import FeatureController
from lp.services.features.model import FeatureFlag, getFeatureStore


class FeatureFixture(Fixture):
    """A fixture that sets a feature.

    The fixture takes a dictonary as its constructor argument. The keys of the
    dictionary are features to be set.

    Call the fixture's `setUp()' method to install the features with the
    desired values.  Calling `cleanUp()' will restore the original values.

    The fixture can also be used as a context manager. The value of the
    feature within the context block is set to the dictonary's key's value.
    The values are restored when the block exits.

    All flags will be set with a priority of 1.
    """

    def __init__(self, features_dict):
        """Constructor."""
        self.desired_features = features_dict

    def setUp(self):
        """Set the feature flags that this fixture is responsible for."""
        super(FeatureFixture, self).setUp()
        self._setup_flags_database()
        self._setup_feature_controller()

    def _setup_flags_database(self):
        store = getFeatureStore()
        for flag, setting in self.desired_features.iteritems():
            flag = store.add(
                    FeatureFlag(
                        scope=u'default',
                        flag=unicode(flag),
                        value=unicode(setting),
                        priority=1))
            self.addCleanup(store.remove, flag)

    def _setup_feature_controller(self):
        # XXX mars 2010-09-22 bug=631884
        # Currently the first features users has to set per-thread
        # features.
        original_features = getattr(per_thread, 'features', None)
        def in_scope(value):
            return True
        per_thread.features = FeatureController(in_scope)
        self.addCleanup(setattr, per_thread, 'features', original_features)
