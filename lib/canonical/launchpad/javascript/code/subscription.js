/*
   Copyright (c) 2009, Canonical Ltd. All rights reserved.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU Affero General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
   GNU Affero General Public License for more details.

   You should have received a copy of the GNU Affero General Public License
   along with this program. If not, see <http://www.gnu.org/licenses/>.
*/

YUI.add('code.branch.subscription', function(Y) {

/*
 * Tools for working with branch subscriptions.
 *
 * @module lp.code.branch.subscription
 * @namespace lp.code.branch.subscription
 */
//TODO: Write documentation.

var namespace = Y.namespace('code.branch.subscription');

var SubscriptionWidget = function(config) {
    SubscriptionWidget.superclass.constructor.apply(this, arguments);
};

SubscriptionWidget.NAME = 'branch-subscription-widget';
SubscriptionWidget.ATTRS = {
    direct_subscribers: {},
    self_subscribe: {},
};
SubscriptionWidget.HTML_PARSER = {
    direct_subscribers: '#subscribers-direct',
    self_subscribe: '.subscribe-self'
};

Y.extend(SubscriptionWidget, Y.Widget, {

    initializer: function () {
        //TODO: subscribe "subscriber updated" to _updateSubscribersList
    },
    renderUI: function () {},
    bindUI: function() {
        //TODO: This needs to use the activator
        var self_subscribe = this.get("self_subscribe");
        self_subscribe.on('click', function(e) {
            // IE tables don't support innerHTML after render.
            if (Y.UA.ie) {
                return;
            }
            e.halt();

            });
    },
    syncUI: function() {
        Y.log(Y.dump(this.get("self_subscription")));
    },

    _updateSubscribersList: function() {
        Y.io('+branch-portlet-subscriber-content', {
            on: {
                success: function(id, response) {
                    Y.get('#subscriber-list').set(
                        'innerHTML', response.responseText);
                    Y.get('#subscriber-list').setStyle('display', 'block');
                    if (highlight) {
                        animate_subscription_update();
                    }
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
    },
    _lp_client: new LP.client.Launchpad(),
    _branch_repr: LP.client.cache.context

});
namespace.SubscriptionWidget = SubscriptionWidget;

}, '0.1', {'requires': [
    'node',
    'dump'
    ]});
