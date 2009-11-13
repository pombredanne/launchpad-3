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

YUI.add('lp.code.branch.subscription', function(Y) {

/*
 * Tools for working with branch subscriptions.
 *
 * @module lp.code.branch.subscription
 * @namespace lp.code.branch.subscription
 */

var namespace = Y.namespace('lp.code.branch.subscription');

var SubscriptionWidget = function() {
    SubscriptionWidget.superclass.constructor.apply(this, arguments);
};

SubscriptionWidget.NAME = 'branch-subscription-widget';
SubscriptionWidget.HTML_PARSER = {
    direct_subscribers: '#subscribers-direct',
    self_subscription: '#selfsubscription',
    //TODO: "Subscribe someone else" is not yet implemented, but we may want to
    //implement it as part of this work.
}

Y.extend(SubscriptionWidget, Y.Widget, {

    initializer: function () {},
    renderUI: function () {},
    bindUI: function() {},
    syncUI: function() {}

});

}, '0.1', {'requires': ['event', 'io', 'node']});
