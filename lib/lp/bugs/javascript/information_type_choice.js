/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Information Type choice widget for bug pages.
 */

YUI.add('lp.bugs.information_type_choice', function(Y) {

var namespace = Y.namespace('lp.bugs.information_type_choice');

namespace.setup_information_type_choice = function(privacy_link) {
    var lp_client = new Y.lp.client.Launchpad();
    var information_type = Y.one('#information-type');
    var information_type_edit = new Y.ChoiceSource({
        editicon: privacy_link,
        contentBox: Y.one('#privacy'),
        value_location: information_type,
        value: LP.cache.bug.information_type,
        title: "Change Information Type",
        items: LP.cache.information_types,
        backgroundColor: '#FFFF99'
    });
    information_type_edit.render();
    information_type_edit.on("save", function(e) {
        var error_handler = new Y.lp.client.ErrorHandler();
        var body = Y.one('body');
        var value = information_type_edit.get('value');
        // This is required due to the display_userdata_as_private feature
        // flag.
        if (value === 'Private') {
            value = 'User Data';
        }
        var private_type = (Y.Array.indexOf(
            LP.cache.private_types, value) >= 0);
        var subscription_ns = Y.lp.bugs.bugtask_index.portlets.subscription;
        var privacy_ns = Y.lp.app.privacy;
        var config = {
            on: {
                success: function(id, response) {
                    subscription_ns.update_subscription_status();
                    if (private_type) {
                        body.replaceClass('public', 'private');
                        privacy_ns.display_privacy_notification();
                    } else {
                        body.replaceClass('private', 'public');
                        privacy_ns.hide_privacy_notification();
                    }
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                information_type: value
            }
        };
        lp_client.named_post(
            LP.cache.bug.self_link, 'transitionToInformationType', config);
    });
    privacy_link.addClass('js-action');
};

}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "lazr.choiceedit",
                        "lp.bugs.bugtask_index.portlets.subscription"]});
