# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Feature flags for Twisted.

Flags are refreshed asynchronously at regular intervals.
"""

__metaclass__ = type
__all__ = ['setup_feature_controller']

from twisted.internet import (
    defer,
    reactor,
    )
from twisted.internet.threads import deferToThread
from twisted.python import log

from lp.services.database import read_transaction
from lp.services.features import (
    getFeatureFlag,
    install_feature_controller,
    make_script_feature_controller,
    )


def setup_feature_controller(script_name):
    '''Install the FeatureController and schedule regular updates.

    Update interval is specified by the twisted.flags.refresh
    feature flag, defaulting to 30 seconds.
    '''
    controller = _new_controller(script_name)
    _install_and_reschedule(controller, script_name)


@defer.inlineCallbacks
def update(script_name):
    controller = yield deferToThread(_new_controller, script_name)
    _install_and_reschedule(controller, script_name)


@read_transaction
def _new_controller(script_name):
    controller = make_script_feature_controller(script_name)
    controller.getAllFlags()  # Pull everything so future lookups don't block.
    return controller


_last_refresh = None


def _install_and_reschedule(controller, script_name):
    install_feature_controller(controller)
    refresh = getFeatureFlag('twisted.flags.refresh') or 60.0
    try:
        refresh = float(refresh)
    except ValueError:
        log.msg("Invalid value {0!r} for twisted.flags.refresh".format(
            refresh))
        refresh = 60.0

    global _last_refresh
    if refresh != _last_refresh:
        if _last_refresh is not None:
            log.msg("twisted.flags.refresh changed to {0}".format(refresh))
        _last_refresh = refresh

    reactor.callLater(refresh, update, script_name)
