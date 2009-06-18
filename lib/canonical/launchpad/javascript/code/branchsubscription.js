/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Subscription handling for branches.
 *
 * @module BranchSubscription
 * @requires base, node, lazr.formoverlay, lazr.anim
 */

YUI.add('code.branchsubscription', function(Y) {

Y.code = {};
Y.code.branchsubscription = {};

/* XXX: rockstar - Bugs shares a similar pattern with is in this regard.  An
 * abstract PortletTarget should be created that we can both share.
 */
var PortletTarget = function() {};
Y.augment(PortletTarget, Y.Event.Target);
Y.code.branchsubscription.portlet = new PortletTarget();

/*
 * Update the subscriber list via Ajax.
 */
Y.code.branchsubscription.update_subscriber_list = function() {

    Y.get('#subscribers-portlet-spinner').setStyle('display', 'block');
    Y.io('+branch-portlet-subscriber-content', {
        on: {
            complete: function(id, response) {
                Y.get('#subscribers-portlet-spinner').setStyle(
                    'display', 'none');
                Y.get('#subscriber-list').set(
                    'innerHTML', response.responseText);

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
            '<button type="submit" name="field.actions.cancel" ' +
            'class="lazr-neg lazr-btn">Cancel</button>'),
        centered: true,
        form_submit_callback: function() {},
        visible: false
    });
    subscription_form_overlay.render();

    /* XXX: rockstar - The form is a bite wide for the current form overlay,
     * and there isn't an easy way to resize it, thus this hack.
     */
    Y.get('#shadow').setStyle('width', '562px');
    Y.get('div#yui-pretty-overlay-modal.content_box_container').setStyle(
        'width', '500px');
}

/*
 * Set up all the things needed for someone to subscribe themselves to a
 * branch.
 */
function set_up_self_subscription_formoverlay(element_id) {

    var subscribe_yourself = Y.get('#selfsubscription');

    if (subscribe_yourself) {

        update_subscription_url = get_element_href(subscribe_yourself);
        var subscription_form_url = update_subscription_url + '/++form++';
        Y.io(subscription_form_url, {
            on: {
                complete: function(id, response) {
                    create_self_subscription_form_overlay(
                        response.responseText);
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


}, '0.1', {requires: ['base', 'oop', 'node', 'event', 'io-base',
    'lazr.formoverlay', 'lazr.anim']});
