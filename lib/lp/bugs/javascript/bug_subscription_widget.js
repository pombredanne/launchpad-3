/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Handling of the bug subscription form overlay widget.
 *
 * @module bugs
 * @submodule bug_subscription_widget
 */
YUI.add('lp.bugs.bug_subscription_widget', function(Y) {

var namespace = Y.namespace('lp.bugs.bug_subscription_widget');

var submit_button_html =
    '<button type="submit" name="field.actions.subscribe" ' +
    'value="Subscribe"' +
    'class="lazr-pos lazr-btn" >OK</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';

namespace.create_subscription_wizard = function() {
    // Create the do-you-want-to-subscribe FormOverlay.
    var wizard_steps = [
        new Y.lazr.wizard.Step({
            form_content: namespace.get_subscribe_form_content(),
            form_submit_button: Y.Node.create(submit_button_html),
            form_cancel_button: Y.Node.create(cancel_button_html),
            funcLoad: function() {},
            funcCleanUp: function() {}
            })
        ];
    var subscribe_wizard = new Y.lazr.wizard.Wizard({
        headerContent: '<h2>Subscribe to this bug</h2>',
        centered: true,
        visible: false,
        steps: wizard_steps
    });
    subscribe_wizard.render('#subscribe-wizard');

    return subscribe_wizard;
};

}, "0.1", {"requires": [
    "base", "io", "oop", "node", "event", "lazr.formoverlay",
    "lazr.effects", "lazr.wizard"]});
