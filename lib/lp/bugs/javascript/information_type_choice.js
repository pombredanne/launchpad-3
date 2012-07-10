/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Information Type choice widget for bug pages.
 */

YUI.add('lp.bugs.information_type_choice', function(Y) {

var namespace = Y.namespace('lp.bugs.information_type_choice');

// For testing.
var skip_animation = false;

/**
 * Lookup the information_type property, keyed on the named value.
 * @param key the key to lookup
 * @param key_name the key property name
 * @param value_name the value property_name
 * @return {*}
 */
var information_type_value_from_key = function(key, key_name,
                                                value_name) {
    var data = null;
    Y.Array.some(LP.cache.information_type_data, function(info_type) {
        if (info_type[key_name] === key) {
            data = info_type[value_name];
            return true;
        }
    });
    return data;
};

namespace.save_information_type = function(widget, value, lp_client) {
    var error_handler = new Y.lp.client.FormErrorHandler();
    error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(
            Y.one('#information-type'), error_msg);
    };
    error_handler.handleError = function(ioId, response) {
        var orig_value = information_type_value_from_key(
            LP.cache.bug.information_type, 'name', 'value');
        widget.set('value', orig_value);
        widget._showFailed();
        update_privacy_portlet(orig_value);
        return false;
    };
    var base_url = LP.cache.context.web_link;
    var submit_url = base_url+"/+secrecy";
    var qs = Y.lp.client.append_qs('', 'field.actions.change', 'Change');
    qs = Y.lp.client.append_qs(qs, 'field.information_type', value);
    var sub_list_node = Y.one('#other-bug-subscribers');
    var subscribers_list = sub_list_node.getData('subscribers_loader');
    var config = {
        method: "POST",
        headers: {'Accept': 'application/xhtml;application/json'},
        data: qs,
        on: {
            start: function () {
                widget._uiSetWaiting();
                subscribers_list.subscribers_list.startActivity(
                    'Updating subscribers...');
            },
            end: function () {
                widget._uiClearWaiting();
                subscribers_list.subscribers_list.stopActivity();
            },
            success: function (id, response) {
                var result_data = null;
                if (response.responseText !== '') {
                    result_data = Y.JSON.parse(response.responseText);
                }
                namespace.information_type_save_success(
                    widget, value, subscribers_list, result_data);
                Y.lp.client.display_notifications(
                    response.getResponseHeader('X-Lazr-Notifications'));
            },
            failure: error_handler.getFailureHandler()
        }
    };
    lp_client.io_provider.io(submit_url, config);
};

var update_privacy_portlet = function(value) {
    var description = information_type_value_from_key(
        value, 'value', 'description');
    var desc_node = Y.one('#information-type-description');
    if (Y.Lang.isValue(desc_node)) {
        desc_node.set('text', description);
    }
    var summary = Y.one('#information-type-summary');
    var private_type = (Y.Array.indexOf(LP.cache.private_types, value) >= 0);
    if (private_type) {
        summary.replaceClass('public', 'private');
    } else {
        summary.replaceClass('private', 'public');
    }
};

var update_privacy_banner = function(value) {
    var body = Y.one('body');
    var privacy_banner = Y.lp.app.banner.privacy.getPrivacyBanner();
    var private_type = (Y.Array.indexOf(LP.cache.private_types, value) >= 0);
    if (private_type) {
        body.replaceClass('public', 'private');
        var banner_text = namespace.get_information_type_banner_text(value);
        privacy_banner.updateText(banner_text);
        privacy_banner.show();
    } else {
        body.replaceClass('private', 'public');
        privacy_banner.hide();
    }
};

namespace.get_information_type_banner_text = function(value) {
    var text_template = "This page contains {info_type} information.";
    var info_type = information_type_value_from_key(value, 'value', 'name');
    if (info_type === "User Data" && LP.cache.show_userdata_as_private) {
            info_type = "Private";
    }
    return Y.Lang.substitute(text_template, {'info_type': info_type});
};

namespace.information_type_save_success = function(widget, value,
                                                   subscribers_list,
                                                   subscribers_data) {
    LP.cache.bug.information_type =
        information_type_value_from_key(value, 'value', 'name');
    update_privacy_banner(value);
    widget._showSucceeded();
    if (Y.Lang.isObject(subscribers_data)) {
        var subscribers = subscribers_data.subscription_data;
        subscribers_list._loadSubscribersFromList(subscribers);
        var cache_data = subscribers_data.cache_data;
        var item;
        for (item in cache_data) {
            if (cache_data.hasOwnProperty(item)) {
                LP.cache[item] = cache_data[item];
            }
        }
    }
    var ns = Y.lp.bugs.bugtask_index.portlets.subscription;
    ns.update_subscription_status(skip_animation);
};

namespace.setup_information_type_choice = function(privacy_link, lp_client,
                                                   skip_anim) {
    skip_animation = skip_anim;
    var initial_value = information_type_value_from_key(
        LP.cache.bug.information_type, 'name', 'value');
    var information_type = Y.one('#information-type');
    var information_type_edit = new Y.ChoiceSource({
        editicon: privacy_link,
        contentBox: Y.one('#privacy'),
        value_location: information_type,
        value: initial_value,
        title: "Change information type",
        items: LP.cache.information_type_data,
        backgroundColor: '#FFFF99',
        flashEnabled: false
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
        update_privacy_portlet(value);
        namespace.save_information_type(
            information_type_edit, value, lp_client);
    });
    privacy_link.addClass('js-action');
    return information_type_edit;
};
}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "lazr.choiceedit", "lp.bugs.bugtask_index",
                        "lp.app.banner.privacy", "lp.app.choice"]});
