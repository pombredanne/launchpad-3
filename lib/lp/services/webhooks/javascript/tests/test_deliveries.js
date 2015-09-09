/* Copyright 2015 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.services.webhooks.deliveries.test', function (Y) {

    var tests = Y.namespace('lp.services.webhooks.deliveries.test');
    tests.suite = new Y.Test.Suite(
        'lp.services.webhooks.deliveries Tests');

    var DELIVERY_PENDING = {
        "event_type": "ping", "successful": null, "error_message": null,
        "date_sent": null, "self_link": "http://example.com/delivery/1",
        "date_created": "2014-09-08T01:19:16+00:00", "date_scheduled": null,
        "pending": true, "resource_type_link": "#webhook_delivery"};

    var DELIVERY_SUCCESSFUL = {
        "event_type": "ping", "successful": true,
        "error_message": null,
        "date_sent": "2014-09-08T01:19:16+00:00",
        "self_link": "http://example.com/delivery/2",
        "date_created": "2014-09-08T01:19:16+00:00",
        "date_scheduled": null, "pending": false,
        "resource_type_link": "#webhook_delivery"};

    var DELIVERY_SUCCESSFUL_RETRY_NOW = {
        "event_type": "ping", "successful": true,
        "error_message": null,
        "date_sent": "2014-09-08T01:19:16+00:00",
        "self_link": "http://example.com/delivery/2",
        "date_created": "2014-09-08T01:19:16+00:00",
        "date_scheduled": "2014-09-08T01:19:16+00:00",
        "pending": true, "resource_type_link": "#webhook_delivery"};

    var DELIVERY_FAILED = {
        "event_type": "ping", "successful": false,
        "error_message": "Bad HTTP response: 404",
        "date_sent": "2014-09-08T01:19:16+00:00",
        "self_link": "http://example.com/delivery/2",
        "date_created": "2014-09-08T01:19:16+00:00",
        "date_scheduled": null, "pending": false,
        "resource_type_link": "#webhook_delivery"};

    var DELIVERY_FAILED_RETRY_SCHEDULED = {
        "event_type": "ping", "successful": false,
        "error_message": "Bad HTTP response: 404",
        "date_sent": "2014-09-08T01:19:16+00:00",
        "self_link": "http://example.com/delivery/2",
        "date_created": "2014-09-08T01:19:16+00:00",
        "date_scheduled": "2034-09-08T01:19:16+00:00", "pending": true,
        "resource_type_link": "#webhook_delivery"};

    var common_test_methods = {

        setUp: function() {
            Y.one("#fixture").append(
                Y.Node.create(Y.one("#fixture-template").getContent()));
            this.widget = this.createWidget();
        },

        tearDown: function() {
            this.widget.destroy();
            Y.one("#fixture").empty();
        },

        createWidget: function(cfg) {
            var config = Y.merge(cfg, {
                srcNode: "#webhook-deliveries",
            });
            var ns = Y.lp.services.webhooks.deliveries;
            return new ns.WebhookDeliveries(config);
        }

    };

    tests.suite.add(new Y.Test.Case(Y.merge(common_test_methods, {
        name: 'lp.services.webhooks.deliveries_tests',

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
            Y.Assert.isFalse(Y.all("#webhook-deliveries tr").isEmpty());
            Y.Assert.isNotNull(Y.one("#webhook-deliveries-table-loading"));
            this.widget.render();
            Y.Assert.isTrue(Y.all("#webhook-deliveries tr").isEmpty());
            Y.Assert.isNull(Y.one("#webhook-deliveries-table-loading"));
            Y.ArrayAssert.itemsAreEqual(this.widget.get("deliveries"), []);
        },

        test_expand_detail: function() {
            this.widget.render();
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 0);
            this.widget.set("deliveries", [DELIVERY_PENDING]);
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 1);
            // Clicking a row adds a new one immediately below with details.
            Y.one("#webhook-deliveries tr:nth-child(1)").simulate("click");
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 2);
            // Clicking on the new row does nothing.
            Y.one("#webhook-deliveries tr:nth-child(2)").simulate("click");
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 2);
            // Adding and clicking another row expands it as well.
            this.widget.set("deliveries", [DELIVERY_PENDING, DELIVERY_FAILED]);
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 3);
            Y.one("#webhook-deliveries tr:nth-child(3)").simulate("click");
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 4);
            // Clicking the main row again collapses it.
            Y.one("#webhook-deliveries tr:nth-child(1)").simulate("click");
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 3);
        },

        test_delivery_pending: function() {
            this.widget.set("deliveries", [DELIVERY_PENDING]);
            this.widget.render();
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 1);
            Y.Assert.isTrue(Y.one("td span.sprite").hasClass("milestone"));
            // Expand the detail section.
            Y.Assert.isNull(Y.one(".delivery-delivering-notice"));
            Y.one("#webhook-deliveries tr").simulate("click");
            Y.Assert.isNotNull(Y.one(".delivery-delivering-notice"));
            // Of the retry widgets, only the "Delivering" spinner is shown.
            Y.Assert.isFalse(
                Y.one(".delivery-delivering-notice").hasClass("hidden"));
            Y.Assert.isTrue(
                Y.one(".delivery-retry-notice").hasClass("hidden"));
            Y.Assert.isTrue(
                Y.one(".delivery-retry").hasClass("hidden"));
        },

        test_delivery_successful: function() {
            var widget = this.createWidget();
            widget.render();
            widget.set("deliveries", [DELIVERY_SUCCESSFUL]);
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 1);
            Y.Assert.isTrue(Y.one("td span.sprite").hasClass("yes"));
            // Expand the detail section.
            Y.Assert.isNull(Y.one(".delivery-delivering-notice"));
            Y.one("#webhook-deliveries tr td").simulate("click");
            Y.Assert.isNotNull(Y.one(".delivery-delivering-notice"));
            // The only visible retry widget is the "Retry" link.
            Y.Assert.isTrue(
                Y.one(".delivery-delivering-notice").hasClass("hidden"));
            Y.Assert.isTrue(
                Y.one(".delivery-retry-notice").hasClass("hidden"));
            Y.Assert.isFalse(
                Y.one(".delivery-retry").hasClass("hidden"));
            Y.Assert.areEqual(Y.one(".delivery-retry").get("text"), "Retry");
        },

        test_delivery_successful_retry_now: function() {
            var widget = this.createWidget();
            widget.render();
            widget.set("deliveries", [DELIVERY_SUCCESSFUL_RETRY_NOW]);
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 1);
            Y.Assert.isTrue(Y.one("td span.sprite").hasClass("yes"));
            // Expand the detail section.
            Y.Assert.isNull(Y.one(".delivery-delivering-notice"));
            Y.one("#webhook-deliveries tr td").simulate("click");
            Y.Assert.isNotNull(Y.one(".delivery-delivering-notice"));
            // The "Delivering" spinner is visible.
            Y.Assert.isFalse(
                Y.one(".delivery-delivering-notice").hasClass("hidden"));
            Y.Assert.isTrue(
                Y.one(".delivery-retry-notice").hasClass("hidden"));
            Y.Assert.isTrue(
                Y.one(".delivery-retry").hasClass("hidden"));
        },

        test_delivery_failed: function() {
            var widget = this.createWidget();
            widget.render();
            widget.set("deliveries", [DELIVERY_FAILED]);
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 1);
            Y.Assert.isTrue(Y.one("td span.sprite").hasClass("no"));
            // Expand the detail section.
            Y.Assert.isNull(Y.one(".delivery-delivering-notice"));
            Y.one("#webhook-deliveries tr td").simulate("click");
            Y.Assert.isNotNull(Y.one(".delivery-delivering-notice"));
            // The only visible retry widget is the "Retry" link.
            Y.Assert.isTrue(
                Y.one(".delivery-delivering-notice").hasClass("hidden"));
            Y.Assert.isTrue(
                Y.one(".delivery-retry-notice").hasClass("hidden"));
            Y.Assert.isFalse(
                Y.one(".delivery-retry").hasClass("hidden"));
            Y.Assert.areEqual(Y.one(".delivery-retry").get("text"), "Retry");
        },

        test_delivery_failed_retry_scheduled: function() {
            var widget = this.createWidget();
            widget.render();
            widget.set("deliveries", [DELIVERY_FAILED_RETRY_SCHEDULED]);
            Y.Assert.areEqual(Y.all("#webhook-deliveries tr").size(), 1);
            Y.Assert.isTrue(Y.one("td span.sprite").hasClass("warning-icon"));
            // Expand the detail section.
            Y.Assert.isNull(Y.one(".delivery-delivering-notice"));
            Y.one("#webhook-deliveries tr td").simulate("click");
            Y.Assert.isNotNull(Y.one(".delivery-delivering-notice"));
            // The visible retry widgets are the schedule notice and a
            // "Retry now" link.
            Y.Assert.isTrue(
                Y.one(".delivery-delivering-notice").hasClass("hidden"));
            Y.Assert.isFalse(
                Y.one(".delivery-retry-notice").hasClass("hidden"));
            Y.Assert.areEqual(
                Y.one(".delivery-retry-notice").get("text"),
                "Retrying on 2034-09-08.");
            Y.Assert.isFalse(
                Y.one(".delivery-retry").hasClass("hidden"));
            Y.Assert.areEqual(
                Y.one(".delivery-retry").get("text"), "Retry now");
        }

    })));

}, '0.1', {'requires': ['test', 'test-console', 'event', 'node-event-simulate',
        'lp.testing.mockio', 'lp.services.webhooks.deliveries']});
