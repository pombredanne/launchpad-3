/* Copyright 2015 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Webhook delivery widgets.
 *
 * @module lp.services.webhooks.deliveries
 */

YUI.add("lp.services.webhooks.deliveries", function(Y) {

var namespace = Y.namespace("lp.services.webhooks.deliveries");

function WebhookDeliveriesListingNavigator(config) {
    WebhookDeliveriesListingNavigator.superclass.constructor.apply(
        this, arguments);
}

WebhookDeliveriesListingNavigator.NAME =
    'webhook-deliveries-listing-navigator';

WebhookDeliveriesListingNavigator.UPDATE_CONTENT = 'updateContent';

Y.extend(WebhookDeliveriesListingNavigator,
         Y.lp.app.listing_navigator.ListingNavigator, {

    initializer: function(config) {
        this.publish(
            namespace.WebhookDeliveriesListingNavigator.UPDATE_CONTENT);
    },

    render_content: function() {
        this.fire(
            namespace.WebhookDeliveriesListingNavigator.UPDATE_CONTENT,
            this.get_current_batch().deliveries);
    },

    _batch_size: function(batch) {
        return batch.deliveries.length;
    }

});

namespace.WebhookDeliveriesListingNavigator =
    WebhookDeliveriesListingNavigator;

function WebhookDeliveries(config) {
    WebhookDeliveries.superclass.constructor.apply(this, arguments);
}

WebhookDeliveries.NAME = "webhook-deliveries";

Y.extend(WebhookDeliveries, Y.Widget, {

    initializer: function(config) {
        // Objects in LP.cache.deliveries are not wrapped on page load,
        // but the objects we get from batch navigation are. Ensure
        // we're always dealing with wrapped ones.
        this.lp_client = new Y.lp.client.Launchpad();
        this.deliveries = this.lp_client.wrap_resource(
            null, LP.cache.deliveries);

        // Set up the batch navigation controls.
        var container = Y.one('#webhook-deliveries');
        var navigator = new namespace.WebhookDeliveriesListingNavigator({
            current_url: window.location,
            cache: LP.cache,
            target: Y.one('#webhook-deliveries-table'),
            container: container,
        });
        navigator.set('backwards_navigation',
                      container.all('.first,.previous'));
        navigator.set('forwards_navigation',
                      container.all('.last,.next'));
        navigator.clickAction('.first', navigator.first_batch);
        navigator.clickAction('.next', navigator.next_batch);
        navigator.clickAction('.previous', navigator.prev_batch);
        navigator.clickAction('.last', navigator.last_batch);
        navigator.update_navigation_links();
        var self = this;
        navigator.subscribe(
            namespace.WebhookDeliveriesListingNavigator.UPDATE_CONTENT,
            function(e) {
                self.deliveries = e.details[0];
                self.syncUI();
            });
        this.navigator = navigator;
    },

    syncUI: function() {
        var table = this.get("contentBox").one("#webhook-deliveries-table");
        var self = this;
        var new_tbody = Y.Node.create("<tbody></tbody>");
        Y.Array.each(this.deliveries, function(delivery) {
            new_tbody.append(self._render_delivery(delivery));
        });
        table.one("tbody").replace(new_tbody);
    },

    _pick_sprite: function(delivery) {
        if (delivery.get("successful") === null) {
            return "milestone";
        } else if (delivery.get("successful")) {
            return "yes";
        } else if (delivery.get("pending")) {
            return "warning-icon";
        } else {
            return "no";
        }
    },

    _render_delivery: function(delivery) {
        var row_template = [
            '<tr>',
            '<td><span class="sprite {{sprite}}" /></td>',
            '<td>{{date}}</td>',
            '<td>{{event_type}}</td>',
            '<td>{{status}}</td>',
            '</tr>'].join(' ');
        context = {
            sprite: this._pick_sprite(delivery),
            date: Y.lp.app.date.approximatedate(
                new Date(delivery.get("date_created"))),
            event_type: delivery.get("event_type"),
            status: delivery.get("error_message")}
        var new_row = Y.lp.mustache.to_html(
            row_template, context);
        return new_row;
    }
});

namespace.WebhookDeliveries = WebhookDeliveries;

}, "0.1", {"requires": ["event", "node", "widget", "lp.app.date",
                        "lp.app.listing_navigator", "lp.client",
                        "lp.mustache"]});
