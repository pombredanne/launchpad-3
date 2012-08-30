/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Information Type choice widget for bug pages.
 */

YUI.add('lp.bugs.information_type_choice', function(Y) {

var namespace = Y.namespace('lp.bugs.information_type_choice');
var information_type = Y.namespace('lp.app.information_type');

// For testing.
var skip_animation = false;

/**
 * Save the new information type. If validate_change is true, then a check
 * will be done to ensure the bug will not become invisible. If the bug will
 * become invisible, a confirmation popup is used to confirm the user's
 * intention. Then this method is called again with validate_change set to
 * false to allow the change to proceed.
 *
 * @param widget
 * @param initial_value
 * @param value
 * @param lp_client
 * @param validate_change
 */
namespace.save_information_type = function(widget, initial_value, value,
                                           lp_client, validate_change) {
    var error_handler = new Y.lp.client.FormErrorHandler();
    error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(
            Y.one('#information-type'), error_msg);
    };
    error_handler.handleError = function(ioId, response) {
        if( response.status === 400
                && response.statusText === 'Bug Visibility') {
            namespace._confirm_information_type_change(
                    widget, initial_value, lp_client);
            return true;
        }
        var orig_value = information_type.information_type_value_from_key(
            LP.cache.bug.information_type, 'name', 'value');
        widget.set('value', orig_value);
        widget._showFailed();
        information_type.update_privacy_portlet(orig_value);
        return false;
    };
    var submit_url = document.URL + "/+secrecy";
    var qs = Y.lp.client.append_qs('', 'field.actions.change', 'Change');
    qs = Y.lp.client.append_qs(qs, 'field.information_type', value);
    qs = Y.lp.client.append_qs(
            qs, 'field.validate_change', validate_change?'on':'off');
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

namespace.information_type_save_success = function(widget, value,
                                                   subscribers_list,
                                                   subscribers_data) {
    LP.cache.bug.information_type =
        information_type.information_type_value_from_key(
                value, 'value', 'name');
    information_type.update_privacy_banner(value);
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

/**
 * Possibly prompt the user to confirm the change of information type.
 * If the old value is public, and the new value is private, we want to
 * confirm that the user really wants to make the change.
 *
 * @param widget
 * @param initial_value
 * @param lp_client
 * @private
 */
namespace._confirm_information_type_change = function(widget, initial_value,
                                                      lp_client) {
    var value = widget.get('value');
    var do_save = function() {
        information_type.update_privacy_portlet(value);
        namespace.save_information_type(
            widget, initial_value, value, lp_client, false);
    };
    // Reset the widget back to it's original value so the user doesn't see it
    // change while the confirmation dialog is showing.
    var new_value = widget.get('value');
    widget.set('value', initial_value);
    information_type.update_privacy_portlet(initial_value);
    var confirm_text_template = [
        '<p class="block-sprite large-warning">',
        '    You are about to mark this bug as ',
        '    <strong>{information_type}</strong>.<br>',
        '    The bug will become invisible because there is no-one with',
        '    permissions to see {information_type} bugs.',
        '</p><p>',
        '    <strong>Please confirm you really want to do this.</strong>',
        '</p>'
        ].join('');
    var title = information_type.information_type_value_from_key(
            value, 'value', 'name');
    var confirm_text = Y.Lang.sub(confirm_text_template,
            {information_type: title});
    var co = new Y.lp.app.confirmationoverlay.ConfirmationOverlay({
        submit_fn: function() {
            widget.set('value', new_value);
            information_type.update_privacy_portlet(new_value);
            do_save();
        },
        form_content: confirm_text,
        headerContent: '<h2>Confirm information type change</h2>'
    });
    co.show();
};

namespace.setup_information_type_choice = function(privacy_link, lp_client,
                                                   skip_anim) {
    skip_animation = skip_anim;
    var initial_value = information_type.information_type_value_from_key(
        LP.cache.bug.information_type, 'name', 'value');
    var information_type_value = Y.one('#information-type');
    var information_type_edit = new Y.ChoiceSource({
        editicon: privacy_link,
        contentBox: Y.one('#privacy'),
        value_location: information_type_value,
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
        information_type.update_privacy_portlet(value);
        namespace.save_information_type(
            information_type_edit, initial_value, value, lp_client, true);

    });
    privacy_link.addClass('js-action');
    return information_type_edit;
};
}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "lazr.choiceedit", "lp.bugs.bugtask_index",
                        "lp.app.banner.privacy", "lp.app.choice",
                        "lp.app.information_type"]});
