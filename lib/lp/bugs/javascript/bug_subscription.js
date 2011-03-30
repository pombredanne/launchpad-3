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
var level_div;

// XXX: gmb 2011-03-17 bug=728457
//      This fix for resizing needs to be incorporated into
//      lazr.effects. When that is done it should be removed from here.
/*
 * Make sure that the bug_notification_level div is hidden properly .
 * @method clean_up_level_div
 */
namespace.clean_up_level_div = function() {
    if (Y.Lang.isValue(level_div)) {
        level_div.setStyles({
            height: 0,
            visibility: 'hidden'
        });
    }
};

namespace.set_up_bug_notification_level_field = function() {
    level_div = Y.one('.bug-notification-level-field');
    var subscription_radio_buttons = Y.all(
        'input[name=field.subscription]');

    // Only collapse the bug_notification_level field if the buttons are
    // available to display it again.
    if (Y.Lang.isValue(level_div) && subscription_radio_buttons.size() > 1) {
        var slide_in_anim = Y.lazr.effects.slide_in(level_div);
        slide_in_anim.on('end', namespace.clean_up_level_div);
        var slide_out_anim = Y.lazr.effects.slide_out(level_div);
        slide_out_anim.on('end', function() {
            level_div.setStyles({
                visibility: 'visible'
            });
        });
        slide_in_anim.run();
        Y.each(subscription_radio_buttons, function(subscription_button) {
            subscription_button.on('click', function(e) {
                if(e.target.get('value') == 'update-subscription') {
                    slide_out_anim.run();
                } else {
                    slide_in_anim.run();
                }
            });
        });
    }
};

}, "0.1", {"requires": ["dom", "node", "io-base", "lazr.anim", "lazr.effects",
    ]});
