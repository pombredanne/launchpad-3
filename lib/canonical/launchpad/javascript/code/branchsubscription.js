/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Subscription handling for branches.
 *
 * @module BranchSubscription
 * @requires base, node, lazr.formoverlay
 */

YUI.add('code.branchsubscription', function(Y) {

Y.code = Y.namespace('code');
Y.code.branchsubscription = Y.namespace = Y.namespace(
    'code.branchsubscription');

/* XXX: rockstar - The Bugs team shares a similar pattern in this regard.  An
 * abstract PortletTarget should be created that we can both share.
 */
var PortletTarget = function() {};
Y.augment(PortletTarget, Y.Event.Target);
Y.code.branchsubscription.portlet = new PortletTarget();

var me;
var display_name;

/*
 * Update the subscriber list via Ajax.
 */
Y.code.branchsubscription.update_subscriber_list = function() {

    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }
    if (lp_branch_entry === undefined) {
        var branch_repr = LP.client.cache.context;
        lp_branch_entry = new LP.client.Entry(
            lp_client, branch_repr, branch_repr.self_link);
    }

    Y.get('#subscriber-list').setStyle('display', 'none');
    Y.get('#subscribers-portlet-spinner').setStyle('display', 'block');
    Y.io('+branch-portlet-subscriber-content', {
        on: {
            success: function(id, response) {
                Y.get('#subscribers-portlet-spinner').setStyle(
                    'display', 'none');
                Y.get('#subscriber-list').set(
                    'innerHTML', response.responseText);
                Y.get('#subscriber-list').setStyle('display', 'block');
            },
            failure: function(id, response) {
                Y.get('#subscriber-list').set(
                    'innerHTML', 'A problem has occurred.');
                Y.log(reponse.responseText);
            },
            complete: function(id, response) {
                Y.code.branchsubscription.portlet.fire(
                    'code:subscriptionsloaded');
            }}});
}


var subscription_form_overlay;
var update_subscription_url;
var lp_client;
var lp_branch_entry;

/*
 * Return the href property of an element.
 */
function get_element_href(element) {
    return element.getAttribute('href');
}

function create_self_subscription_form_overlay(form_content) {
    subscription_form_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Subscribe to branch</h2>',
        form_content: form_content,
        form_submit_button: Y.Node.create(
            '<button type="submit" name="field.actions.change" ' +
            'value="Change" class="lazr-pos lazr-btn">Ok</button>'),
        form_cancel_button: Y.Node.create(
            '<button type="button" name="field.actions.cancel" ' +
            'class="lazr-neg lazr-btn">Cancel</button>'),
        centered: true,
        form_submit_callback: subscribe_yourself_inline,
        visible: false
    });
    subscription_form_overlay.render();

    /* XXX: rockstar - bug=389185 - The form is a bit wide for the current
     * form overlay, and there isn't an easy way to resize it, thus this hack.
     */
    Y.get('#shadow').setStyle('width', '562px');
    Y.get('div#yui-pretty-overlay-modal.content_box_container').setStyle(
        'width', '500px');
}

/*
 * Handle the submission of the form overlay.
 */
function subscribe_yourself_inline(data) {

    subscription_form_overlay.hide();

    me = LP.client.links.me;
    add_temp_user_name()

    /* XXX: rockstar - bug=389188 - Select boxes don't pass the data across
     * the way the API is expecting it to come.  This basically means that
     * the data passed into this function is worthless in this situation.
     */
    var notification_level = document.getElementById(
        'field.notification_level')
    var notification_level_update = notification_level.options[
        notification_level.selectedIndex].text;
    var max_diff_lines = document.getElementById(
        'field.max_diff_lines')
    var max_diff_lines_update = max_diff_lines.options[
        max_diff_lines.selectedIndex].text;
    var review_level = document.getElementById(
        'field.review_level')
    var review_level_update = review_level.options[
        review_level.selectedIndex].text;

    config = {
        on: {
            success: function(updated_entry) {
                lp_subscription_entry = updated_entry;

                // XXX: rockstar: bug=336866 The etag returned by lp_save() is
                // totally wrong.
                lp_subscription_entry.removeAtt('http_etag');

                Y.get('#selfsubscription').set(
                    'innerHTML', 'Edit your subscription');

                Y.code.branchsubscription.update_subscriber_list();
            },
            failure: function(id, response) {
                Y.log(response.responseText);
                alert('An error has occurred.  Please try again.');
                subscription_form_overlay.show();
            }
        },
        parameters: {
            person: LP.client.get_absolute_uri(me),
            notification_level: notification_level_update,
            max_diff_lines: max_diff_lines_update,
            code_review_level: review_level_update
        }
    };

    lp_client.named_post(LP.client.cache.context.self_link,
        'subscribe', config);
}

/*
 * Set up all the things needed for someone to subscribe themselves to a
 * branch.
 */
function set_up_self_subscription_formoverlay(element_id) {

    var subscribe_yourself = Y.get('#selfsubscription');

    if (subscribe_yourself !== null) {

        update_subscription_url = get_element_href(subscribe_yourself);
        var subscription_form_url = update_subscription_url + '/++form++';
        Y.io(subscription_form_url, {
            on: {
                success: function(id, response) {
                    create_self_subscription_form_overlay(
                        response.responseText);
                },
                failure: function(id, response) {
                    Y.log(response.responseText);
                }}});
        subscribe_yourself.on('click', function(e) {
            e.preventDefault();
            subscription_form_overlay.show();
        });
    }
}
Y.code.branchsubscription.portlet.subscribe(
    'code:subscriptionsloaded', set_up_self_subscription_formoverlay);


/*
 * Hides the "Edit your subscription" link.
 */
function hide_edit_your_subscription() {
    var element = Y.get('#selfsubscription');
    if (element.get('innerHTML') == 'Edit your subscription') {
        element.setStyle('display', 'none');
    }
}
Y.code.branchsubscription.portlet.subscribe(
    'code:subscriptionsloaded', hide_edit_your_subscription);


/*
 * Add the greyed out user name.
 * XXX: rockstar - This is also stolen from bugs, and modified slightly.  It
 * needs to be abstracted.
 */
function add_temp_user_name() {
    var img_src = '/@@/persongray';

    var html = [
        '<div id="temp-username">',
        '  <img src="' + img_src + '" alt="" width="14" height="14" /> ',
        display_name,
        '  <img id="temp-name-spinner" src="/@@/spinner" alt="" ',
        '    style="position:absolute;right:8px" /></div>'].join('');
    var link_node = Y.Node.create(html);

    var subscribers = Y.get('#subscriber-list');
    var next = subscribers.query('div')[0];
    if (next) {
        subscribers.insertBefore(link_node, next);
    } else {
        // Handle the case of the displayed "None".
        var none_subscribers = Y.get('#none-subscribers');
        if (none_subscribers) {
            var none_parent = none_subscribers.get('parentNode');
            none_parent.removeChild(none_subscribers);
        }
        subscribers.appendChild(link_node);
    }
}


/*
 * Initialize the various variables for referring to "me".
 * XXX: rockstar - This code was also kiped from bugs, and will need to be
 * abstracted.
 */
function setup_names() {
    me = LP.client.links.me;
    user_name = get_user_name_from_uri(me);

    // There is no need to set display_name if it exists.
    if (display_name !== undefined) {
        return;
    }

    config = {
        on: {
            success: function(person) {
                display_name = person.lookup_value('display_name');
            }
        }
    };
    lp_client.get(me, config);
}
Y.code.branchsubscription.portlet.subscribe(
    'code:subscriptionsloaded', setup_names);

/*
 * Take a user_uri of the form "/~username" and return
 * just the username.  Ex., "/~deryck" becomes "deryck".
 *
 * @method get_user_name_from_uri
 * @param user_uri {String} The user's URI, without the hostname.
 * @return name {String} The user's name.
 */
function get_user_name_from_uri(user_uri) {
    var name = user_uri.substring(2);
    return name;
}



}, '0.1', {requires: ['base', 'oop', 'node', 'event', 'io-base',
    'lazr.formoverlay']});
