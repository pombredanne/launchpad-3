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

WebhookDeliveries.ATTRS = {

    deliveries: {
        value: [],
        setter: function(deliveries) {
            var self = this;
            // Objects in LP.cache.deliveries are not wrapped on page
            // load, but the objects we get from batch navigation are.
            // Ensure we're always dealing with wrapped ones.
            return Y.Array.map(deliveries, function(delivery) {
                if (delivery.get === undefined) {
                    return self.lp_client.wrap_resource(null, delivery);
                } else {
                    return delivery;
                }
            });
        }
    }

};

Y.extend(WebhookDeliveries, Y.Widget, {

    initializer: function(config) {
        this.lp_client = new Y.lp.client.Launchpad();
        this.delivery_info = {};

        var self = this;
        this.after("deliveriesChange", function(e) {
            // Populate the delivery_info map for any deliveries we
            // haven't seen before, and refresh any that we have.
            Y.Array.each(self.get("deliveries"), function(res) {
                if (!Y.Object.owns(self.delivery_info, res.get("self_link"))) {
                    self.delivery_info[res.get("self_link")] = {
                        resource: res, expanded: false,
                        requesting_retry: false};
                } else {
                    self.delivery_info[res.get("self_link")].resource = res;
                }
            });
            // Update the list of delivery URLs to display.
            self.deliveries_displayed = Y.Array.map(
                self.get("deliveries"),
                function(res) {return res.get("self_link");});
            if (self.get("rendered")) {
                self.syncUI();
            }
        });
    },

    bindUI: function() {
        var table = this.get("contentBox").one("#webhook-deliveries-table");
        table.delegate("click", this._toggle_detail.bind(this), "tbody > tr");
        table.delegate(
            "click", this._trigger_retry.bind(this), ".delivery-retry");
    },

    syncUI: function() {
        var table = this.get("contentBox").one("#webhook-deliveries-table");
        var new_tbody = Y.Node.create("<tbody></tbody>");
        var self = this;
        Y.Array.each(this.deliveries_displayed, function(delivery_url) {
            var delivery = self.delivery_info[delivery_url];
            var resource = delivery.resource;
            var delivery_node = self._render_delivery(resource);
            new_tbody.append(delivery_node);
            if (delivery.expanded) {
                var detail_node = self._render_detail(delivery_node);
                delivery_node.setData('delivery-detail-tr', detail_node);
                new_tbody.append(detail_node);
                var date_scheduled =
                    resource.get("date_scheduled") !== null
                    ? Y.lp.app.date.parse_date(resource.get("date_scheduled"))
                    : null;
                var retrying_now =
                    delivery.requesting_retry || (
                        resource.get("pending") && (
                            date_scheduled === null
                            || date_scheduled < new Date()));
                if (retrying_now) {
                    // Retrying already, or we're currently requesting one.
                    detail_node.one(".delivery-retry-notice").addClass("hidden");
                    detail_node.one(".delivery-retry").addClass("hidden");
                    detail_node.one(".delivery-delivering-notice")
                        .removeClass("hidden");
                } else if (resource.get("pending")) {
                    // Retry scheduled for the future.
                    var retrying_text =
                        Y.lp.app.date.approximatedate(date_scheduled);
                    detail_node.one(".delivery-retry-notice").set(
                        "text", "Retrying " + retrying_text + ".");
                    detail_node.one(".delivery-retry").set("text", "Retry now");
                    detail_node.one(".delivery-retry-notice").removeClass("hidden");
                    detail_node.one(".delivery-retry").removeClass("hidden");
                    detail_node.one(".delivery-delivering-notice").addClass("hidden");
                } else {
                    var retry_text = resource.successful ? "Redeliver" : "Retry";
                    detail_node.one(".delivery-retry").set("text", retry_text);
                    detail_node.one(".delivery-retry-notice").addClass("hidden");
                    detail_node.one(".delivery-delivering-notice").addClass("hidden");
                    detail_node.one(".delivery-retry").removeClass("hidden");
                }
            }
        });
        table.one("tbody").replace(new_tbody);
    },

    _pick_sprite: function(delivery) {
        if (delivery.get("pending") && delivery.get("successful") === null) {
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
                Y.lp.app.date.parse_date(delivery.get("date_created"))),
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
            '<span class="delivery-retry-notice hidden"></span> ',
            '<a class="js-action delivery-retry">Retry</a>',
            '<span class="delivery-delivering-notice hidden">',
            '  <img src="/@@/spinner" /> Delivering',
            '</span>',
            '</div>',
            '</td>',
            '</tr>'].join(''));
        detail_node.setData('delivery-tr', delivery_node);
        detail_node.one('span.text').set(
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
        var delivery = this.delivery_info[delivery_url];
        delivery.expanded = !delivery.expanded;
        this.syncUI();
    },

    _trigger_retry: function(e) {
        var detail_node = e.currentTarget.ancestor('tr', false);
        var delivery_url =
            detail_node.getData('delivery-tr').getData('delivery-url');
        var delivery = this.delivery_info[delivery_url];
        if (delivery.requesting_retry) {
            // Already in progress.
            return;
        }
        delivery.requesting_retry= true;
        this.syncUI();
        var self = this;
        var config = {
            on: {
                success: function() {
                    // TODO: Refresh the object and unset this.
                    delivery.requesting_retry = false;
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
