# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enumerations and related utilities used in the lp/app modules."""

__metaclass__ = type
__all__ = [
    'ServiceUsage',
    'service_uses_launchpad',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )


class ServiceUsage(DBEnumeratedType):
    """Launchpad application usages.

    Indication of a pillar's usage of Launchpad for the various services:
    bug tracking, translations, code hosting, blueprint, and answers.
    """

    UNKNOWN = DBItem(10, """
    Unknown

    The maintainers have not indicated usage.  This value is the default for
    new pillars.
    """)

    LAUNCHPAD = DBItem(20, """
    Launchpad

    Launchpad is used to provide this service.
    """)

    EXTERNAL = DBItem(30, """
    External

    The service is provided external to Launchpad.
    """)

    NOT_APPLICABLE = DBItem(40, """
    Not Applicable

    The pillar does not use this type of service in Launchpad or externally.
    """)


def service_uses_launchpad(usage_enum):
    return usage_enum == ServiceUsage.LAUNCHPAD


class InformationVisibilityPolicy(DBEnumeratedType):
    """Information Visibility Policy.

    The policies used to control which users and teams can see various
    Launchpad artifacts, including bugs and branches.
    """

    PUBLIC = DBItem(1, """
        Public

        Everyone can see this information.
        """)

    PUBLICSECURITY = DBItem(2, """
        Public Security

        Everyone can see this information pertaining to a resolved security
        related bug.
        """)

    EMBARGOEDSECURITY = DBItem(3, """
        Embargoed Security

        Only users with permission to see the project's security related
        artifacts can see this information.
        """)

    USERDATA = DBItem(4, """
        User Data

        Only users with permission to see the project's artifacts containing
        user data can see this information.
        """)

#    PROPRIETARY = DBItem(5, """
#        Proprietary
#
#        Only users with permission to see the project's artifacts containing
#        proprietary data can see this information.
#        """)
