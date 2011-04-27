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

var bug_notification_level_visible = false;

function is_notification_level_shown(value, is_subscribed,
                                     can_update_subscription) {
    // Is the new selected option the "subscribe me" option?
    // It is when there is no existing subscription, and
    // when either the selected radio box is for the current user.
    var needs_to_subscribe = (
        (is_subscribed === false) && ('/~' + value === LP.links.me));

    // Notification levels selection box is shown when either the
    // radio box is for updating a subscription to set the level,
    // or if a user wants to subscribe.
    if ((value === 'update-subscription') ||
        (needs_to_subscribe === true && can_update_subscription === false)) {
        return true;
    } else {
        return false;
    }
}

function needs_toggling(current_value, new_value,
                        is_subscribed, can_update_subscription) {
    if (current_value !== new_value) {
        var was_shown = is_notification_level_shown(
            current_value, is_subscribed, can_update_subscription);
        var should_be_shown = is_notification_level_shown(
            new_value, is_subscribed, can_update_subscription);
        return was_shown !== should_be_shown;
    } else {
        return false;
    }
}

var slideout_animation;
var slideout_running = false;

function toggle_bug_notification_level(level_div, quick) {
    var config = {};
    if (quick === true) {
        config.duration = 0.001;
    }
    if (!bug_notification_level_visible) {
        slideout_animation = Y.lazr.effects.slide_out(level_div, config);
        slideout_animation.after('end', function () {
            slideout_running = false;
        });
        slideout_running = true;
        slideout_animation.run();
    } else {
        if (Y.Lang.isValue(slideout_animation) && slideout_running) {
            // it's currently expanding, stop that animation
            // and slide in.
            slideout_animation.stop();
        }
        Y.lazr.effects.slide_in(level_div, config).run();
    }
    bug_notification_level_visible = !bug_notification_level_visible;
}

namespace.set_up_bug_notification_level_field = function(config) {
    var level_div = Y.one('.bug-notification-level-field');
    var subscription_radio_buttons = Y.all('input[name=field.subscription]');
    var is_subscribed = config.is_subscribed_already;

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

        // Level options are always initially shown in the form.
        bug_notification_level_visible = true;
        var should_be_shown = is_notification_level_shown(
            current_value, is_subscribed, can_update_sub);
        if (bug_notification_level_visible !== should_be_shown) {
            toggle_bug_notification_level(level_div, true);
        }

        subscription_radio_buttons.each(function(subscription_button) {
            subscription_button.on('click', function(e) {
                var value = e.target.get('value');
                if (value !== current_value) {
                    if (needs_toggling(current_value, value,
                                       is_subscribed, can_update_sub)) {
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
