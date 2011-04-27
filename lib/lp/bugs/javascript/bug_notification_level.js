/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Animation for IBugTask:+subscribe LaunchpadForm.
 * Also used in "Edit subscription" advanced overlay.
 *
 * @namespace Y.lp.bugs.bug_notification_level
 * @requires  dom, "node, lazr.anim, lazr.effects
 */
YUI.add('lp.bugs.bug_notification_level', function(Y) {
var namespace = Y.namespace('lp.bugs.bug_notification_level');

/**
 * Should notification level options be shown for these conditions?
 *
 * @param value {String} Value of the selected radio box.  Special
 *     value 'update-subscription' is used for the radio box that
 *     indicates editing of the existing subscription.
 * @param can_update_subscription {Boolean} Is there a radio box to
 *     update the existing subscription.  If there is, it is the only
 *     radio button that should show the notification level options.
 * @returns {Boolean} True if notification level options should be shown
 *     for this set of conditions.
 */
function is_notification_level_shown(value, can_update_subscription) {
    // Is the new selected option the "subscribe me" option?
    // It is when there is no existing subscription, and
    // when either the selected radio box is for the current user.
    var needs_to_subscribe = (
        (can_update_subscription === false) &&
            ('/~' + value === LP.links.me));

    // Notification levels selection box is shown when either the
    // radio box is for updating a subscription to set the level,
    // or if a user wants to subscribe.
    if ((value === 'update-subscription') || needs_to_subscribe) {
        return true;
    } else {
        return false;
    }
}
namespace._is_notification_level_shown = is_notification_level_shown;

/**
 * Is the change of the radio boxes such that the notification level options
 * need toggling.
 *
 * @param current_value {String} Previously selected radio button value.
 * @param new_value {String} Newly selected radio button value.
 * @param can_update_subscription {Boolean} Is there a radio box to
 *     update the existing subscription.  If there is, it is the only
 *     radio button that should show the notification level options.
 * @returns {Boolean} True if change from `current_value` to `new_value`
 *     requires toggling the visibility of bug notification level options.
 */
function needs_toggling(current_value, new_value, can_update_subscription) {
    if (current_value !== new_value) {
        var was_shown = is_notification_level_shown(
            current_value, can_update_subscription);
        var should_be_shown = is_notification_level_shown(
            new_value, can_update_subscription);
        return was_shown !== should_be_shown;
    } else {
        return false;
    }
}
namespace._needs_toggling = needs_toggling;

/**
 * Slide-out animation used in the toggle_field_visibility() needs
 * to be stopped if someone quickly selects an option that triggers the
 * slide-in animation.  We keep these globally to be able to stop
 * the running animation.
 */
var slideout_animation;
var slideout_running = false;

/**
 * Is the bug_notification_level visible in the current view.
 * A global state that we alternate with toggle_field_visibility().
 */
var bug_notification_level_visible = true;

/**
 * Change the visibility of the bug notification level options.
 * Uses appropriate animation for nicer effect.
 *
 * @param level_div {Object} A Y.Node to show/hide.
 * @param quick_close {Boolean} Should animation be short-circuited?
 *     Useful for initial set-up, and only allows closing the node.
 */
function toggle_field_visibility(level_div, quick_close) {
    var config = {};
    if (quick_close === true) {
        level_div.setStyle('display', 'none');
        level_div.addClass('lazr-closed');
        bug_notification_level_visible = false;
        return;
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

/**
 * Set-up showing of bug notification levels as appropriate in the
 * bug subscription form.
 *
 * There can not be more than one advanced subscription overlay, or
 * this code is going to break.
 *
 * This form is visible on either IBugTask:+subscribe page, or in the
 * advanced subscription overlay on the IBugTask pages (when
 * 'Edit subscription' or 'Unmute' is clicked).
 */
namespace.setup = function() {
    var level_div = Y.one('.bug-notification-level-field');
    var subscription_radio_buttons = Y.all('input[name=field.subscription]');

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
            current_value, can_update_sub);
        if (bug_notification_level_visible !== should_be_shown) {
            toggle_field_visibility(level_div, true);
        }

        subscription_radio_buttons.each(function(subscription_button) {
            subscription_button.on('click', function(e) {
                var value = e.target.get('value');
                if (value !== current_value) {
                    if (needs_toggling(current_value, value,
                                       can_update_sub)) {
                        toggle_field_visibility(level_div);
                    }
                }
                current_value = value;
            });
        });
    }
};

}, "0.1", {"requires": ["dom", "node", "lazr.anim", "lazr.effects"
    ]});
