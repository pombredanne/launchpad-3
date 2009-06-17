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
Y.code.subscriptionportlet = new PortletTarget();


// TODO: add a setup type function here.
Y.code.subscriptionportlet.subscribe('code:subscriptionportletloaded',
    function() {}
);

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

                var element = Y.get('.menu-link-subscription');
                if (element.get('innerHTML') == 'Edit your subscription') {
                    element.setStyle('display', 'none');
                }
            }}});
}

});
