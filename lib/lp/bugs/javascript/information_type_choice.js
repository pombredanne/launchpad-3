/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Information Type choice widget for bug pages.
 */

YUI.add('lp.bugs.information_type_choice', function(Y) {

var namespace = Y.namespace('lp.bugs.information_type_choice');
var information_type_descriptions = {};

// For testing.
var skip_animation = false;

namespace.save_information_type = function(widget, value, lp_client) {
    var error_handler = new Y.lp.client.ErrorHandler();
    error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(
            Y.one('#information-type'), error_msg);
    };
    error_handler.handleError = function(ioId, response) {
        var orig_value = LP.cache.bug.information_type;
        widget.set('value', orig_value);
        update_information_type_description(orig_value);
        return false;
    };
    var config = {
        on: {
            start: Y.bind(widget._uiSetWaiting),
            end: Y.bind(widget._uiClearWaiting),
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

namespace.get_information_type_banner_text = function(value) {
    var fallback_text = "The information on this page is private.";
    var text_template = "This page contains {info_type} information.";

    if (value === "User Data" && LP.cache.show_userdata_as_private) {
            value = "Private";
    }
    if (LP.cache.show_information_type_in_ui) {
        return Y.Lang.substitute(text_template, {'info_type': value});
    } else {
        return fallback_text;
    }
};

namespace.information_type_save_success = function(value) {
    var body = Y.one('body');
    var private_type = (Y.Array.indexOf(LP.cache.private_types, value) >= 0);
    var subscription_ns = Y.lp.bugs.bugtask_index.portlets.subscription;
    var privacy_banner = Y.lp.app.banner.privacy.getPrivacyBanner();
    subscription_ns.update_subscription_status(skip_animation);
    if (private_type) {
        var banner_text = namespace.get_information_type_banner_text(value);
        privacy_banner.updateText(banner_text);
        body.replaceClass('public', 'private');
        privacy_banner.show();
    } else {
        body.replaceClass('private', 'public');
        privacy_banner.hide();
    }
};

namespace.setup_information_type_choice = function(privacy_link, lp_client,
                                                   skip_anim) {
    skip_animation = skip_anim;
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
    Y.lp.app.choice.hook_up_choicesource_spinner(information_type_edit);
    information_type_edit.render();
    information_type_edit.on("save", function(e) {
        var value = information_type_edit.get('value');
        // This is required due to the display_userdata_as_private feature
        // flag.
        if (value === 'Private') {
            value = 'User Data';
        }
        update_information_type_description(value);
        namespace.save_information_type(
            information_type_edit, value, lp_client);
    });
    privacy_link.addClass('js-action');
    return information_type_edit;
};
}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "lazr.choiceedit", "lp.bugs.bugtask_index",
                        "lp.app.banner.privacy", "lp.app.choice"]});
