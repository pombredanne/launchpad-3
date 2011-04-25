/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * A bugtracker form overlay that can create a bugtracker within any page.
 *
 * @namespace Y.lp.bugs.bugtracker_overlay
 * @requires  dom, node, io-base, lazr.anim, lazr.formoverlay
 */
YUI.add('lp.bugs.bug_subscription', function(Y) {
var namespace = Y.namespace('lp.bugs.bug_subscription');

function needs_toggling(value, is_subscribed, can_update_subscription) {
    var needs_to_subscribe = (
        ('/~' + value === LP.links.me) && (is_subscribed === false));
    if ((value === 'update-subscription') ||
        (needs_to_subscribe === true && can_update_subscription === false)) {
        return true;
    } else {
        return false;
    }
}

var slideout_animation;
var slideout_running = false;

function toggle_bug_notification_level(level_div) {
    var hidden = !level_div.hasClass('level-expanded');
    var slideout, slidein;

    if (hidden) {
        level_div.addClass('level-expanded');
        slideout_animation = Y.lazr.effects.slide_out(level_div);
        slideout_animation.after('end', function () {
            slideout_running = false;
        });
        slideout_running = true;
        slideout_animation.run();
    } else {
        level_div.removeClass('level-expanded');
        if (Y.Lang.isValue(slideout_animation) && slideout_running) {
            // it's currently expanding, stop that animation
            // and slide in.
            slideout_animation.stop();
        }
        Y.lazr.effects.slide_in(level_div).run();
    }
}

namespace.set_up_bug_notification_level_field = function(is_subscribed) {
    var level_div = Y.one('.bug-notification-level-field');
    var subscription_radio_buttons = Y.all(
        'input[name=field.subscription]');

    // Only collapse the bug_notification_level field if the buttons are
    // available to display it again.
    if (Y.Lang.isValue(level_div) && subscription_radio_buttons.size() > 1) {
        // Get current value from the selected radio box.
        var checked_box = subscription_radio_buttons.filter(':checked').pop();
        var current_value = checked_box.get('value');

        // Is there a radio box for changing the bug notification level?
        var can_update_sub = (
            subscription_radio_buttons
                .filter('[value="update-subscription"]')
                .size() === 1);

        if (needs_toggling(current_value, is_subscribed, can_update_sub)) {
            toggle_bug_notification_level(level_div);
        }
        Y.each(subscription_radio_buttons, function(subscription_button) {
            subscription_button.on('click', function(e) {
                var value = e.target.get('value');
                if (value !== current_value) {
                    if (needs_toggling(
                            value, is_subscribed, can_update_sub) ||
                        needs_toggling(
                            current_value, is_subscribed, can_update_sub)) {
                        //debugger;
                        toggle_bug_notification_level(level_div);
                    }
                }
                current_value = value;
            });
        });
    }
};

}, "0.1", {"requires": ["dom", "node", "io-base", "lazr.anim", "lazr.effects"
    ]});
