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
    // Construct the form. This is a bit hackish but it saves us from
    // having to try to get information from TAL into JavaScript and all
    // the horror that entails.
    var subscribe_form_body =
        '<div>' +
        '    <p>Tell me when</p>' +
        '    <table>' +
        '       <tr>' +
        '         <td>' +
        '           <input type="radio" name="field.bug_notification_level" ' +
        '               id="bug-notification-level-comments"' +
        '               value="Discussion"' +
        '               class="bug-notification-level" />' +
        '         </td>' +
        '         <td>' +
        '           <label for="bug-notification-level-comments">' +
        '             A change is made or a comment is added to this bug' +
        '           </label>' +
        '         </td>' +
        '     </tr>' +
        '     <tr>' +
        '       <td>' +
        '         <input type="radio" name="field.bug_notification_level" ' +
        '             id="bug-notification-level-metadata" value="Details"' +
        '             class="bug-notification-level" />' +
        '       </td>' +
        '       <td>' +
        '         <label for="bug-notification-level-metadata">' +
        '             A change is made to the bug; do not notify me about ' +
        '             new comments.' +
        '         </label>' +
        '       </td>' +
        '     </tr>' +
        '     <tr>' +
        '       <td>' +
        '         <input type="radio" name="field.bug_notification_level" ' +
        '             id="bug-notification-level-lifecycle" value="Lifecycle"' +
        '             class="bug-notification-level" />' +
        '       </td>' +
        '       <td>' +
        '         <label for="bug-notification-level-lifecycle">' +
        '           Changes are made to the bug\'s status.' +
        '         </label>' +
        '       </td>' +
        '     </tr>' +
        '  </table>' +
        '</div>';

    // Create the do-you-want-to-subscribe FormOverlay.
    var wizard_steps = [
        new Y.lazr.wizard.Step({
            form_content: subscribe_form_body,
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
