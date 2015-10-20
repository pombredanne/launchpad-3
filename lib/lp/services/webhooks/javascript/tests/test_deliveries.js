/* Copyright 2015 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.services.webhooks.deliveries.test', function (Y) {

    var tests = Y.namespace('lp.services.webhooks.deliveries.test');
    tests.suite = new Y.Test.Suite(
        'lp.services.webhooks.deliveries Tests');
    var lp_client = new Y.lp.client.Launchpad();

    var DELIVERY_PENDING = lp_client.wrap_resource(null, {
        "event_type": "ping", "successful": null, "error_message": null,
        "date_sent": null, "self_link": "http://example.com/delivery/1",
        "date_created": "2014-09-08T01:19:16+00:00", "date_scheduled": null,
        "pending": true, "resource_type_link": "#webhook_delivery"});

    var DELIVERY_SUCCESSFUL = lp_client.wrap_resource(null, {
        "event_type": "ping", "successful": true,
        "error_message": null,
        "date_sent": "2014-09-08T01:19:16+00:00",
        "self_link": "http://example.com/delivery/2",
        "date_created": "2014-09-08T01:19:16+00:00",
        "date_scheduled": null, "pending": false,
        "resource_type_link": "#webhook_delivery"});

    var DELIVERY_SUCCESSFUL_RETRY_NOW = lp_client.wrap_resource(null, {
        "event_type": "ping", "successful": true,
        "error_message": null,
        "date_sent": "2014-09-08T01:19:16+00:00",
        "self_link": "http://example.com/delivery/2",
        "date_created": "2014-09-08T01:19:16+00:00",
        "date_scheduled": "2014-09-08T01:19:16+00:00",
        "pending": true, "resource_type_link": "#webhook_delivery"});

    var DELIVERY_FAILED = lp_client.wrap_resource(null, {
        "event_type": "ping", "successful": false,
        "error_message": "Bad HTTP response: 404",
        "date_sent": "2014-09-08T01:19:16+00:00",
        "self_link": "http://example.com/delivery/2",
        "date_created": "2014-09-08T01:19:16+00:00",
        "date_scheduled": null, "pending": false,
        "resource_type_link": "#webhook_delivery"});

    var DELIVERY_FAILED_RETRY_SCHEDULED = lp_client.wrap_resource(null, {
        "event_type": "ping", "successful": false,
        "error_message": "Bad HTTP response: 404",
        "date_sent": "2014-09-08T01:19:16+00:00",
        "self_link": "http://example.com/delivery/2",
        "date_created": "2014-09-08T01:19:16+00:00",
        "date_scheduled": "2034-09-08T01:19:16+00:00", "pending": true,
        "resource_type_link": "#webhook_delivery"});

    var common_test_methods = {

        setUp: function() {
            Y.one("#fixture").append(
                Y.Node.create(Y.one("#fixture-template").getContent()));
            this.widget = this.createWidget();
            this.node = Y.one("#test-deliveries");
        },

        tearDown: function() {
            this.widget.destroy();
            Y.one("#fixture").empty();
        },

        createWidget: function(cfg) {
            var config = Y.merge(cfg, {
                srcNode: "#test-deliveries",
            });
            var ns = Y.lp.services.webhooks.deliveries;
            return new ns.WebhookDeliveries(config);
        }

    };

    tests.suite.add(new Y.Test.Case(Y.merge(common_test_methods, {
        name: 'lp.services.webhooks.deliveries_widget_tests',

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.services.webhooks.deliveries,
                "Could not locate the " +
                "lp.services.webhooks.deliveries module");
        },

        test_widget_can_be_instantiated: function() {
            Y.Assert.isInstanceOf(
                Y.lp.services.webhooks.deliveries.WebhookDeliveries,
                this.widget, "Widget failed to be instantiated");
        },

        test_render: function() {
            Y.Assert.isFalse(this.node.all("tr").isEmpty());
            Y.Assert.isNotNull(
                this.node.one(".webhook-deliveries-table-loading"));
            this.widget.render();
            Y.Assert.isTrue(this.node.all("tr").isEmpty());
            Y.Assert.isNull(
                this.node.one(".webhook-deliveries-table-loading"));
            Y.ArrayAssert.itemsAreEqual(this.widget.get("deliveries"), []);
        },

        test_expand_detail: function() {
            this.widget.render();
            Y.Assert.areEqual(this.node.all("tr").size(), 0);
            this.widget.set("deliveries", [DELIVERY_PENDING]);
            Y.Assert.areEqual(this.node.all("tr").size(), 1);
            // Clicking a row adds a new one immediately below with details.
            this.node.one("tr:nth-child(1)").simulate("click");
            Y.Assert.areEqual(this.node.all("tr").size(), 2);
            // Clicking on the new row does nothing.
            this.node.one("tr:nth-child(2)").simulate("click");
            Y.Assert.areEqual(this.node.all("tr").size(), 2);

            // Adding and clicking another row expands it as well.
            this.widget.set("deliveries", [DELIVERY_PENDING, DELIVERY_FAILED]);
            Y.Assert.areEqual(this.node.all("tr").size(), 3);
            Y.one("#test-deliveries tr:nth-child(3)").simulate("click");
            Y.Assert.areEqual(this.node.all("tr").size(), 4);
            // Clicking the main row again collapses it.
            this.node.one("tr:nth-child(1)").simulate("click");
            Y.Assert.areEqual(this.node.all("tr").size(), 3);

            // The expanded state is remembered even if the deliveries
            // disappear.
            this.widget.set("deliveries", []);
            Y.Assert.areEqual(this.node.all("tr").size(), 0);
            this.widget.set("deliveries", [DELIVERY_PENDING, DELIVERY_FAILED]);
            Y.Assert.areEqual(this.node.all("tr").size(), 3);
        },

        dump_row_state: function(node) {
            // XXX wgrant 2015-09-09: Should get the detail row in a
            // nicer way.
            Y.Assert.isNull(this.node.one("tr:nth-child(2)"));
            // Expand the detail section.
            node.simulate("click");
            var detail_node = this.node.one("tr:nth-child(2)");
            Y.Assert.isObject(detail_node);
            var delivering_notice = detail_node.one(
                ".delivery-delivering-notice");
            Y.Assert.isNotNull(delivering_notice);
            var retry_notice = detail_node.one(".delivery-retry-notice");
            var retry = detail_node.one(".delivery-retry");
            return {
                sprite: node.one("td span.sprite").get("className"),
                delivering: !delivering_notice.hasClass("hidden"),
                retry_notice: retry_notice.hasClass("hidden")
                    ? null : retry_notice.get("text"),
                retry: retry.hasClass("hidden") ? null : retry.get("text")
                };
        },

        assert_rows_match: function(actual, expected) {
            Y.Assert.areSame(actual.sprite, expected.sprite);
            Y.Assert.areSame(actual.delivering, expected.delivering);
            Y.Assert.areSame(actual.retry_notice, expected.retry_notice);
            Y.Assert.areSame(actual.retry, expected.retry);
        },

        test_delivery_pending: function() {
            this.widget.set("deliveries", [DELIVERY_PENDING]);
            this.widget.render();
            Y.Assert.areEqual(this.node.all("tr").size(), 1);
            var state = this.dump_row_state(this.node.one("tr"));
            // Of the retry widgets, only the "Delivering" spinner is shown.
            Y.Assert.areEqual(state.sprite, "sprite milestone");
            Y.Assert.isTrue(state.delivering);
            Y.Assert.isNull(state.retry_notice);
            Y.Assert.isNull(state.retry);
        },

        test_delivery_successful: function() {
            this.widget.set("deliveries", [DELIVERY_SUCCESSFUL]);
            this.widget.render();
            Y.Assert.areEqual(this.node.all("tr").size(), 1);
            var state = this.dump_row_state(this.node.one("tr"));
            // The only visible retry widget is the "Retry" link.
            Y.Assert.areEqual(state.sprite, "sprite yes");
            Y.Assert.isFalse(state.delivering);
            Y.Assert.isNull(state.retry_notice);
            Y.Assert.areEqual(state.retry, "Retry");
        },

        test_delivery_successful_retry_now: function() {
            this.widget.set("deliveries", [DELIVERY_SUCCESSFUL_RETRY_NOW]);
            this.widget.render();
            Y.Assert.areEqual(this.node.all("tr").size(), 1);
            var state = this.dump_row_state(this.node.one("tr"));
            // The "Delivering" spinner is visible.
            Y.Assert.areEqual(state.sprite, "sprite yes");
            Y.Assert.isTrue(state.delivering);
            Y.Assert.isNull(state.retry_notice);
            Y.Assert.isNull(state.retry);
        },

        test_delivery_failed: function() {
            this.widget.set("deliveries", [DELIVERY_FAILED]);
            this.widget.render();
            Y.Assert.areEqual(this.node.all("tr").size(), 1);
            var state = this.dump_row_state(this.node.one("tr"));
            // The only visible retry widget is the "Retry" link.
            Y.Assert.areEqual(state.sprite, "sprite no");
            Y.Assert.isFalse(state.delivering);
            Y.Assert.isNull(state.retry_notice);
            Y.Assert.areEqual(state.retry, "Retry");
        },

        test_delivery_failed_retry_scheduled: function() {
            this.widget.set("deliveries", [DELIVERY_FAILED_RETRY_SCHEDULED]);
            this.widget.render();
            Y.Assert.areEqual(this.node.all("tr").size(), 1);
            var state = this.dump_row_state(this.node.one("tr"));
            // The visible retry widgets are the schedule notice and a
            // "Retry now" link.
            Y.Assert.areEqual(state.sprite, "sprite warning-icon");
            Y.Assert.isFalse(state.delivering);
            Y.Assert.areEqual(state.retry_notice, "Retrying on 2034-09-08.");
            Y.Assert.areEqual(state.retry, "Retry now");
        },

        test_retry: function() {
            this.widget.set("deliveries", [DELIVERY_FAILED]);
            this.widget.render();
            Y.Assert.areEqual(this.node.all("tr").size(), 1);

            // The delivery is initially not delivering.
            var initial_state =
                this.dump_row_state(this.node.one("tr"));
            Y.Assert.areEqual(initial_state.sprite, "sprite no");
            Y.Assert.isFalse(initial_state.delivering);
            Y.Assert.isNull(initial_state.retry_notice);
            Y.Assert.areEqual(initial_state.retry, "Retry");

            // Hit retry and the delivery spinner is shown.
            this.node.one("tr .delivery-retry").simulate("click");
            this.node.one("tr").simulate("click");
            var retry_state = this.dump_row_state(this.node.one("tr"));
            Y.Assert.areEqual(retry_state.sprite, "sprite warning-icon");
            Y.Assert.isTrue(retry_state.delivering);
            Y.Assert.isNull(retry_state.retry_notice);
            Y.Assert.isNull(retry_state.retry);

            // If the retry request fails, the retry action returns.
            this.widget.delivery_retried(
                "http://example.com/delivery/2", false);
            this.node.one("tr").simulate("click");
            var retry_failed_state = this.dump_row_state(this.node.one("tr"));
            this.assert_rows_match(retry_failed_state, initial_state);

            // Retry again.
            this.node.one("tr .delivery-retry").simulate("click");
            this.node.one("tr").simulate("click");
            var retry_again_state = this.dump_row_state(this.node.one("tr"));
            this.assert_rows_match(retry_again_state, retry_state);

            // Succeed this time and the "Delivering" notice sticks.
            this.widget.delivery_retried(
                "http://example.com/delivery/2", true);
            this.node.one("tr").simulate("click");
            var retried_state = this.dump_row_state(this.node.one("tr"));
            this.assert_rows_match(retried_state, retry_state);
        }

    })));

}, '0.1', {'requires': ['test', 'test-console', 'event', 'node-event-simulate',
        'lp.testing.mockio', 'lp.services.webhooks.deliveries']});
