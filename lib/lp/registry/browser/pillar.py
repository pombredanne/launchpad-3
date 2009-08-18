# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Common views for objects that implement `IPillar`."""

__metaclass__ = type

__all__ = [
    'PillarView',
    ]


from canonical.launchpad.webapp.publisher import LaunchpadView


class PillarView(LaunchpadView):
    """A view for any `IPillar`."""

    @property
    def has_involvement(self):
        """This `IPillar` uses Launchpad."""
        pillar = self.context
        return (
            pillar.official_codehosting or pillar.official_malone
            or pillar.official_answers or pillar.official_blueprints
            or pillar.official_rosetta)
