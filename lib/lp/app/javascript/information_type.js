/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Base functionality for displaying Information Type data.
 */

YUI.add('lp.app.information_type', function(Y) {

var ns = Y.namespace('lp.app.information_type');

/**
 * Any time the information type changes during a page we need an event we can
 * watch out for that.
 *
 * @event information_type:change
 * @param value The new information type value.
 */
Y.publish('information_type:change', {
    emitFacade: true
});

/*
 * We also want shortcuts we can use to fire specific events if the new
 * information type is public or private (generally speaking).
 *
 * @event information_type:is_public
 * @param value The new information type value.
 */
Y.publish('information_type:is_public', {
    emitFacade: true
});

/**
 * The information type has been changed to a private type.
 *
 * @event information_type:is_private
 * @param value The new information type value.
 */
Y.publish('information_type:is_private', {
    emitFacade: true
});

/**
 * Wire up a helper event so that if someone changes the event, we take care
 * of also firing any is_private/is_public event shortcuts others want to
 * listen on.
 *
 * This enables us to keep the looking up of information type to ourselves
 * instead of having each module needing to know the location in the LP.cache
 * and such.
 */
Y.on('information_type:change', function (ev) {
    if (!ev.value) {
        throw('Information type change event without new value');
    }

    if (ns.get_cache_data_from_key(ev.value,
                                  'value',
                                  'is_private')) {
        Y.fire('information_type:is_private', {
            value: ev.value
        });
    } else {
        Y.fire('information_type:is_public', {
            value: ev.value
        });
    }
});


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
ns.save = function(widget, initial_value, value,
                                           lp_client, context,
                                           subscribers_list, validate_change) {
    var error_handler = new Y.lp.client.FormErrorHandler();
    error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(
            Y.one('#information-type'), error_msg);
    };
    error_handler.handleError = function(ioId, response) {
        if( response.status === 400
                && response.statusText === 'Bug Visibility') {
            ns._confirm_change(
                    widget, initial_value, lp_client, context,
                    subscribers_list);
            return true;
        }
        var orig_value = ns.get_cache_data_from_key(
            context.information_type, 'name', 'value');
        widget.set('value', orig_value);
        widget._showFailed();
        ns.update_privacy_portlet(orig_value);
        return false;
    };
    var submit_url = document.URL + "/+secrecy";
    var qs = Y.lp.client.append_qs('', 'field.actions.change', 'Change');
    qs = Y.lp.client.append_qs(qs, 'field.information_type', value);
    qs = Y.lp.client.append_qs(
            qs, 'field.validate_change', validate_change?'on':'off');
    var config = {
        method: "POST",
        headers: {'Accept': 'application/xhtml;application/json'},
        data: qs,
        on: {
            start: function () {
                widget._uiSetWaiting();
                if (Y.Lang.isValue(subscribers_list)){
                    subscribers_list.subscribers_list.startActivity(
                        'Updating subscribers...');
                }
            },
            end: function () {
                widget._uiClearWaiting();
                if (Y.Lang.isValue(subscribers_list)){
                    subscribers_list.subscribers_list.stopActivity();
                }
            },
            success: function (id, response) {
                var result_data = null;
                if (response.responseText !== '' &&
                    response.getResponseHeader('Content-Type') ===
                    'application/json')
                {
                    result_data = Y.JSON.parse(response.responseText);
                }
                ns.save_success(
                    widget, context, value, subscribers_list, result_data);
                Y.lp.client.display_notifications(
                    response.getResponseHeader('X-Lazr-Notifications'));
            },
            failure: error_handler.getFailureHandler()
        }
    };
    lp_client.io_provider.io(submit_url, config);
};

var get_banner_text = function(value) {
    var text_template = "This page contains {info_type} information.";
    var info_type = ns.get_cache_data_from_key(value, 'value', 'name');
    return Y.Lang.sub(text_template, {'info_type': info_type});
};

ns.save_success = function(widget, context, value, subscribers_list,
                           subscribers_data) {
    context.information_type =
        ns.get_cache_data_from_key(value, 'value', 'name');
    ns.update_privacy_banner(value);
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
    if (Y.Lang.isValue(subscribers_list)){
        var subscription_ns = Y.lp.bugs.bugtask_index.portlets.subscription;
        subscription_ns.update_subscription_status(skip_animation);
    }
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
ns._confirm_change = function(widget, initial_value, lp_client, context,
                              subscribers_list) {
    var value = widget.get('value');
    var do_save = function() {
        ns.update_privacy_portlet(value);
        ns.save(
            widget, initial_value, value, lp_client, context, subscribers_list,
            false);
    };
    // Reset the widget back to it's original value so the user doesn't see it
    // change while the confirmation dialog is showing.
    var new_value = widget.get('value');
    widget.set('value', initial_value);
    ns.update_privacy_portlet(initial_value);
    var confirm_text_template = [
        '<p class="block-sprite large-warning">',
        '    You are about to mark this bug as ',
        '    <strong>{information_type}</strong>.<br/>',
        '    The bug will become invisible because there is no-one with',
        '    permissions to see {information_type} bugs.',
        '</p><p>',
        '    <strong>Please confirm you really want to do this.</strong>',
        '</p>'
        ].join('');
    var title = ns.get_cache_data_from_key(value, 'value', 'name');
    var confirm_text = Y.Lang.sub(confirm_text_template,
            {information_type: title});
    var co = new Y.lp.app.confirmationoverlay.ConfirmationOverlay({
        submit_fn: function() {
            widget.set('value', new_value);
            ns.update_privacy_portlet(new_value);
            do_save();
        },
        form_content: confirm_text,
        headerContent: '<h2>Confirm information type change</h2>',
        submit_text: 'Confirm'
    });
    co.show();
};

ns.setup_choice = function(privacy_link, lp_client, context, subscribers_list,
                           skip_anim) {
    skip_animation = skip_anim;
    var initial_value = ns.get_cache_data_from_key(
        context.information_type, 'name', 'value');
    var information_type_value = Y.one('#information-type');
    var choice_list = ns.cache_to_choicesource(
        LP.cache.information_type_data);

    var information_type_edit = new Y.ChoiceSource({
        editicon: privacy_link,
        contentBox: Y.one('#privacy'),
        value_location: information_type_value,
        value: initial_value,
        title: "Change information type",
        items: choice_list,
        backgroundColor: '#FFFF99',
        flashEnabled: false
    });
    Y.lp.app.choice.hook_up_choicesource_spinner(information_type_edit);
    information_type_edit.render();
    information_type_edit.on("save", function(e) {
        var value = information_type_edit.get('value');
        ns.update_privacy_portlet(value);
        ns.save(
            information_type_edit, initial_value, value, lp_client, context,
            subscribers_list, true);
    });
    privacy_link.addClass('js-action');
    return information_type_edit;
};

/**
 * Lookup the information_type property, keyed on the named value.
 *
 * We might want to find based on the name Public or the value PUBLIC so we
 * allow for the user to request what cache field to search on.
 *
 * @param cache_key_value the key value to lookup
 * @param key_property_name the key property name used to access the key value
 * @param value_property_name the value property name
 * @return {*}
 */
ns.get_cache_data_from_key = function(cache_value,
                                              cache_field,
                                              data_field) {
    var cache = LP.cache.information_type_data;
    for (var key in cache) {
        if (cache[key][cache_field] === cache_value) {
            return cache[key][data_field];
        }
    }
};


/**
 * The LP.cache for information type data is an object and needs to be sent to
 * the choicesource as a list of ordered data.
 *
 * @function cache_to_choicesource
 * @param {Object}
 *
 */
ns.cache_to_choicesource = function (cache) {
    var data = [];
    for (var key in cache) {
        data.push(cache[key]);
    }
    // We need to order data based on the order attribute.
    data.sort(function(a, b) { return a.order - b.order; });
    return data;
};

/**
 * Update the privacy portlet to display the specified information type value.
 *
 * @param value
 */
ns.update_privacy_portlet = function(value) {
    var description = ns.get_cache_data_from_key(
        value, 'value', 'description');
    var desc_node = Y.one('#information-type-description');
    if (Y.Lang.isValue(desc_node)) {
        desc_node.set('text', description);
    }
    var summary = Y.one('#information-type-summary');
    var private_type = LP.cache.information_type_data[value].is_private;
    if (private_type) {
        summary.replaceClass('public', 'private');
    } else {
        summary.replaceClass('private', 'public');
    }
};

/**
 * Update the privacy banner to display the specified information type value.
 *
 * @param value
 */
ns.update_privacy_banner = function(value) {
    var body = Y.one('body');
    var privacy_banner = Y.lp.app.banner.privacy.getPrivacyBanner();
    var private_type = LP.cache.information_type_data[value].is_private;
    if (private_type) {
        body.replaceClass('public', 'private');
        var banner_text = get_banner_text(value);
        privacy_banner.updateText(banner_text);
        privacy_banner.show();
    } else {
        body.replaceClass('private', 'public');
        privacy_banner.hide();
    }
};

}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "lp.ui.choiceedit", "lp.bugs.bugtask_index",
                        "lp.app.banner.privacy", "lp.app.choice"]});
