/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Handling of the bug subscription form overlay widget.
 *
 * @module bugs
 * @submodule bug_subscription_wizard
 */
YUI.add('lp.bugs.bug_subscription_wizard', function(Y) {

var namespace = Y.namespace('lp.bugs.bug_subscription_wizard');

var submit_button_html =
    '<button type="submit" name="field.actions.subscribe" ' +
    'value="Subscribe"' +
    'class="lazr-pos lazr-btn" >OK</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';

namespace.subscription_wizard = null;

namespace.create_subscription_wizard = function() {
    // Create the do-you-want-to-subscribe FormOverlay.
    var wizard_steps = [
        new Y.lazr.wizard.Step({
            form_content: namespace.subscribe_form_body,
            form_submit_button: Y.Node.create(submit_button_html),
            form_cancel_button: Y.Node.create(cancel_button_html),
            funcLoad: function() {},
            funcCleanUp: function() {}
            })
        ];
    namespace.subscription_wizard = new Y.lazr.wizard.Wizard({
        headerContent: '<h2>Subscribe to this bug</h2>',
        centered: true,
        visible: false,
        steps: wizard_steps
    });
    namespace.subscription_wizard.render('#subscribe-wizard');
    Y.fire('subscriptionwizard:ready');
};

/**
 * Load the subscription form from a remote source.
 *
 * @method load_subscription_form
 */
namespace.load_subscription_form = function() {
    Y.fire('subscriptionform:loaded');
};

/**
 * Initialize the subscription wizard and set up event handlers.
 *
 * @method initialize_subscription_wizard
 */
namespace.initialize_subscription_wizard = function() {
    Y.on(
        'subscriptionform:loaded',
        Y.bind(function(e) { namespace.create_subscription_wizard() }));
};

}, "0.1", {"requires": [
    "base", "io", "oop", "node", "event", "lazr.formoverlay",
    "lazr.effects", "lazr.wizard"]});
