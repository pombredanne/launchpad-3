/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Subscription handling for branches.
 *
 * @module BranchSubscription
 * @requires base, node, lazr.formoverlay, lazr.anim
 */

YUI.add('code.branchsubscription', function(Y) {

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

// TODO: figure out the best way to approach this.
function SubscriptionListingWidget(config) {
    SubscriptionListingWidget.superclass.constructor.apply(this, arguments);
}


});
