/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Information Type choice widget for bug pages.
 */

YUI.add('lp.bugs.information_type_choice', function(Y) {

var namespace = Y.namespace('lp.bugs.information_type_choice');
var information_type_descriptions = {};

namespace.save_information_type = function(value, lp_client) {
    var error_handler = new Y.lp.client.ErrorHandler();
    var config = {
        on: {
            success: function(id, response) {
                namespace.information_type_save_success(value);
            },
            failure: error_handler.getFailureHandler()
        },
        parameters: {
            information_type: value
        }
    };
    lp_client.named_post(
        LP.cache.bug.self_link, 'transitionToInformationType', config);
};

var update_information_type_description = function(value) {
    var description = information_type_descriptions[value];
    var desc_node = Y.one('#information-type-description');
    if (Y.Lang.isValue(desc_node)) {
        desc_node.set('text', description);
    }
};

namespace.information_type_save_success = function(value) {
    var body = Y.one('body');
    var private_type = (Y.Array.indexOf(LP.cache.private_types, value) >= 0);
    var subscription_ns = Y.lp.bugs.bugtask_index.portlets.subscription;
    var text_template = "This page contains {info_type} information.";
    var text = Y.Lang.substitute(
        text_template, { info_type: value.toLowerCase()});
    var privacy_banner = Y.lp.app.banner.privacy.getPrivacyBanner();
    privacy_banner.updateText(text);
    subscription_ns.update_subscription_status();
    update_information_type_description(value);
    if (private_type) {
        body.replaceClass('public', 'private');
        privacy_banner.show();
    } else {
        body.replaceClass('private', 'public');
        privacy_banner.hide();
    }
};

namespace.setup_information_type_choice = function(privacy_link, lp_client) {
    Y.Array.each(LP.cache.information_types, function(info_type) {
        information_type_descriptions[info_type.value] = info_type.description;
    });
    var information_type = Y.one('#information-type');
    var information_type_edit = new Y.ChoiceSource({
        editicon: privacy_link,
        contentBox: Y.one('#privacy'),
        value_location: information_type,
        value: LP.cache.bug.information_type,
        title: "Change information type",
        items: LP.cache.information_types,
        backgroundColor: '#FFFF99'
    });
    information_type_edit.render();
    information_type_edit.on("save", function(e) {
        var value = information_type_edit.get('value');
        // This is required due to the display_userdata_as_private feature
        // flag.
        if (value === 'Private') {
            value = 'User Data';
        }
        namespace.save_information_type(value, lp_client);
    });
    privacy_link.addClass('js-action');
};
}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "lazr.choiceedit", "lp.bugs.bugtask_index",
                        "lp.app.banner.privacy"]});
