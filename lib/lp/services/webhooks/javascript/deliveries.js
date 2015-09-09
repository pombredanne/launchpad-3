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
        this.deliveries = {};
        var self = this;
        Y.Array.each(LP.cache.deliveries, function(delivery) {
            var resource = self.lp_client.wrap_resource(null, delivery);
            self.deliveries[resource.get("self_link")] = {
                resource: resource, expanded: false, retrying: false};
        });

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
        navigator.subscribe(
            namespace.WebhookDeliveriesListingNavigator.UPDATE_CONTENT,
            function(e) {
                self.deliveries = e.details[0];
                self.syncUI();
            });
        this.navigator = navigator;
    },

    bindUI: function() {
        var table = this.get("contentBox").one("#webhook-deliveries-table");
        table.delegate("click", this._toggle_detail.bind(this), "tbody > tr");
        table.delegate(
            "click", this._trigger_redeliver.bind(this),
            ".delivery-redeliver");
    },

    syncUI: function() {
        var table = this.get("contentBox").one("#webhook-deliveries-table");
        var self = this;
        var new_tbody = Y.Node.create("<tbody></tbody>");
        Y.Object.each(this.deliveries, function(delivery) {
            var resource = delivery.resource;
            var delivery_node = self._render_delivery(resource);
            new_tbody.append(delivery_node);
            if (delivery.expanded) {
                var detail_node = self._render_detail(delivery_node);
                delivery_node.setData('delivery-detail-tr', detail_node);
                new_tbody.append(detail_node);
                if (delivery.retrying) {
                    detail_node.one(".delivery-redeliver-spinner")
                        .removeClass("hidden");
                }
            }
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
            status: delivery.get("error_message")};
        var new_row = Y.Node.create(Y.lp.mustache.to_html(
            row_template, context));
        new_row.setData("delivery-url", delivery.get("self_link"));
        return new_row;
    },

    _render_detail: function(delivery_node) {
        var detail_node = Y.Node.create([
            '<tr>',
            '<td></td>',
            '<td colspan="3" class="webhook-delivery-detail">',
            '<span class="text"></span>',
            '<div>',
            '<a class="js-action delivery-redeliver">Redeliver</a> ',
            '<img src="/@@/spinner"',
            '    class="delivery-redeliver-spinner hidden" />',
            '</div>',
            '</td>',
            '</tr>'].join(''));
        detail_node.setData('delivery-tr', delivery_node);
        detail_node.one('span').set(
            'text',
            'Detail for ' + delivery_node.getData('delivery-url'));
        return detail_node;
    },

    _toggle_detail: function(e) {
        var delivery_url = e.currentTarget.getData('delivery-url');
        if (delivery_url === undefined) {
            // Not actually a delivery row.
            return;
        }
        var delivery = this.deliveries[delivery_url];
        delivery.expanded = !delivery.expanded;
        this.syncUI();
    },

    _trigger_redeliver: function(e) {
        var detail_node = e.currentTarget.ancestor('tr', false);
        var delivery_url =
            detail_node.getData('delivery-tr').getData('delivery-url');
        var delivery = this.deliveries[delivery_url];
        if (delivery.retrying) {
            // Already in progress.
            return;
        }
        delivery.retrying = true;
        this.syncUI();
        var self = this;
        var config = {
            on: {
                success: function() {
                    delivery.retrying = false;
                    self.syncUI();
                }
            }
        };
        this.lp_client.named_post(delivery_url, 'retry', config);
    }

});

namespace.WebhookDeliveries = WebhookDeliveries;

}, "0.1", {"requires": ["event", "node", "widget", "lp.app.date",
                        "lp.app.listing_navigator", "lp.client",
                        "lp.mustache"]});
