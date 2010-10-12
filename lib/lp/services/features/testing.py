# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for writing tests that use feature flags."""

__metaclass__ = type
__all__ = ['active_features']


from fixtures import Fixture
from lp.services.features import per_thread


class FeatureFixture(Fixture):
    """A fixture that sets a feature.

    The fixture takes a dictonary as its constructor argument. The keys of the
    dictionary are features to be set.

    Call the fixture's `setUp()' method to install the features with the
    desired values.  Calling `cleanUp()' will restore the original values.
    You can also install this fixture by inheriting from
    `fixtures.TestWithFixtures' and then calling the TestCase's
    `self.useFixture()' method.

    The fixture can also be used as a context manager. The value of the
    feature within the context block is set to the dictonary's key's value.
    The values are restored when the block exits.
    """

    def __init__(self, features_dict):
        """Constructor.

        :param features_dict: A dictionary-like object with keys and values
            that are flag names and those flags' settings.
        """
        self.desired_features = features_dict

    def setUp(self):
        """Set the feature flags that this fixture is responsible for."""
        super(FeatureFixture, self).setUp()

        controller = FakeFeatureController()

        # Save the currently set features and their controller
        original_features = getattr(per_thread, 'features', None)
        if original_features:
            controller.update(original_features.getAllFlags())

        # Add our new flags, overriding old ones if necessary
        controller.update(self.desired_features)

        per_thread.features = controller
        self.addCleanup(setattr, per_thread, 'features', original_features)


class FakeFeatureController:
    """A FeatureController test double that does not hit the database.

    This is essentially a glorified dict :)
    """

    def __init__(self, scopes_callback=None):
        self._flags = dict()

    def getFlag(self, flag_name):
        """See `FeatureController.getFlag' for usage."""
        return self._flags.get(flag_name)

    def getAllFlags(self):
        """See `FeatureController.getAllFlags' for usage."""
        return self._flags.copy()

    def setFlag(self, flag_name, value):
        """A convenience method for setting a feature flag.

        :param flag_name: The name of the flag to be set.
        :param value: The flag's new value.
        """
        self._flags[flag_name] = value

    def update(self, flags_dict):
        """A convenience method for updating all of the flags in controller.

        :param flags_dict: A dictionary of flag names and values.
        """
        for flag, value in flags_dict.iteritems():
            self.setFlag(flag, value)
