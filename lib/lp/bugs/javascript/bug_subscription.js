/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * A bugtracker form overlay that can create a bugtracker within any page.
 *
 * @namespace Y.lp.bugs.bugtracker_overlay
 * @requires  dom, node, io-base, lazr.anim, lazr.formoverlay
 */
YUI.add('lp.bugs.bugsubscription', function(Y) {
var namespace = Y.namespace('lp.bugs.bugsubscription');

namespace.set_up_bug_notification_level_field = function() {
    var level_div = Y.one('.bug-notification-level-field');
    if (Y.Lang.isValue(level_div)) {
        var slide_in_anim = Y.lazr.effects.slide_in(level_div);
        slide_in_anim.on('end', function() {
            level_div.setStyles({
                height: 0,
                visibility: 'hidden'
            });
        });
        var slide_out_anim = Y.lazr.effects.slide_out(level_div);
        slide_out_anim.on('end', function() {
            level_div.setStyles({
                visibility: 'visible'
            });
        });
        slide_in_anim.run();
        var unmute_radio_buttons = Y.all(
            'input[name=field.subscription]');
        Y.each(unmute_radio_buttons, function(unmute_button) {
            unmute_button.on('click', function(e) {
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
