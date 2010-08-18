/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Handling of the bug subscription form overlay widget.
 *
 * @module bugs
 * @submodule filebug_dupefinder
 */
YUI.add('lp.bugs.filebug_dupefinder', function(Y) {

var namespace = Y.namespace('lp.bugs.subscription_overlay');

namespace.create_subscription_overlay = function() {
    // Construct the form. This is a bit hackish but it saves us from
    // having to try to get information from TAL into JavaScript and all
    // the horror that entails.
    var subscribe_form_body =
        '<div style="width: 320px">' +
        '    <p>Tell me when</p>' +
        '    <p>' +
        '       <input type="radio" name="field.bug_notification_level" ' +
        '           id="bug-notification-level-comments" value="Discussion"' +
        '           class="bug-notification-level" />' +
        '       <label for="bug-notification-level-comments">' +
        '         Any change is made to this bug, including new comments' +
        '       </label>' +
        '       <input type="radio" name="field.bug_notification_level" ' +
        '           id="bug-notification-level-metadata" value="Details"' +
        '           class="bug-notification-level" />' +
        '       <label for="bug-notification-level-metadata">' +
        '         Any change other than a new comment is made to this bug' +
        '       </label>' +
        '       <input type="radio" name="field.bug_notification_level" ' +
        '           id="bug-notification-level-lifecycle" value="Lifecycle"' +
        '           class="bug-notification-level" />' +
        '       <label for="bug-notification-level-lifecycle">' +
        '         Changes are made to the bug\'s status.' +
        '       </label>' +
        '    </p>' +
        '</div>';

    // Create the do-you-want-to-subscribe FormOverlay.
    subscribe_form_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Subscribe to this bug</h2>',
        form_content: subscribe_form_body,
        form_submit_button: Y.Node.create(submit_button_html),
        form_cancel_button: Y.Node.create(cancel_button_html),
        centered: true,
        visible: false
    });
    subscribe_form_overlay.render('#duplicate-overlay-bug-' + bug_id);
};

}, "0.1", {"requires": [
    "base", "io", "oop", "node", "event", "lazr.formoverlay", "lazr.effects"]});
