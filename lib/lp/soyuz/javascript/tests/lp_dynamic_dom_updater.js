/* Copyright 2009 Canonical Ltd.  This software is licensed under the
   GNU Affero General Public License version 3 (see the file LICENSE). */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use('test', 'console', 'lp.soyuz.dynamic_dom_updater', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("DynamicDomUpdater Tests");

suite.add(new Y.Test.Case({

    name: 'dom_updater',

    setUp: function() {
        this.eg_div = Y.Node.create(
            '<div>Default text to start with.</div>');
        this.config = {
            domUpdateFunction: function(node, data_object) {
                node.set('innerHTML', data_object.msg);
            }
        };
    },

    test_dom_updater_is_pluggable: function() {
        // Plugging the DomUpdater adds an 'updater' attribute.
        Assert.isUndefined(
            this.eg_div.updater,
            "Sanity check: initially there is no updater attribute.");

        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DomUpdater, this.config);

        Assert.isNotUndefined(
            this.eg_div.updater,
            "After plugging, the object has an 'updater' attribute.");

        Assert.isInstanceOf(
            Y.lp.soyuz.dynamic_dom_updater.DomUpdater,
            this.eg_div.updater,
            "DomUpdater was not plugged correctly.");
    },

    test_update_function_called_with_correct_params: function() {
        // Calling the update function results in the user-provided update
        // receiving the correct data.
        Assert.areEqual(
            'Default text to start with.',
            this.eg_div.get('innerHTML'),
            "Sanity check that the innerHTML of our example div has not" +
                "been modified.");

        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DomUpdater, this.config);
        this.eg_div.updater.update({msg: "Boo. I've changed."});
        Assert.areEqual(
            "Boo. I've changed.",
            this.eg_div.get('innerHTML'),
            "The user-provided function is executed with the " +
                "supplied data.");
    }
}));

suite.add(new Y.Test.Case({

    name: 'dynamic_dom_updater',

    setUp: function() {
        this.eg_div = Y.Node.create(
            '<div>Default text to start with.</div>');
        this.lp_client_mock = Y.Mock();
        this.config = {
            domUpdateFunction: function(node, data_object) {
                node.set('innerHTML', data_object.msg);
            },
            uri: 'http://example.com',
            api_method_name: 'my_method',
            interval: 1,
            lp_client: this.lp_client_mock,
            long_processing_time: 10,
            short_processing_time: 5
        };

        // We expect only one named_get call on the lp client
        Y.Mock.expect(this.lp_client_mock, {
            method: "named_get",
            args: ['http://example.com', 'my_method', Y.Mock.Value.Object],
            callCount: 1
        });
    },

    test_dynamic_dom_updater_is_pluggable: function() {
        // Plugging the DomUpdater adds an 'updater' attribute.

        Assert.isUndefined(
            this.eg_div.updater,
            "Sanity check: initially there is no updater attribute.");

        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater, this.config);

        Assert.isNotUndefined(
            this.eg_div.updater,
            "After plugging, the object has an 'updater' attribute.");

        Assert.isInstanceOf(
            Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater,
            this.eg_div.updater,
            "DynamicDomUpdater was not plugged correctly.");
    },

    test_no_further_request_if_previous_response_not_received: function() {
        // Requests to the LP API should only be re-issued if a successful
        // response was received previously.

        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater, this.config);

        // Verify that our expectation of only one named_get was met:
        this.wait(function() {
            Y.Mock.verify(this.lp_client_mock);
        }, 5);
    },

    test_second_response_when_previous_request_successful: function() {
        // A second request to the LP API should be issued if the
        // response from the first was successfully received

        // Set an expectation for two calls to named_get
        Y.Mock.expect(this.lp_client_mock, {
            method: "named_get",
            args: ['http://example.com', 'my_method', Y.Mock.Value.Object],
            callCount: 2
        });

        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater, this.config);

        // Wait 5ms just to ensure that the DynamicDomUpdater finishes
        // its initialization.
        this.wait(function() {
            this.eg_div.updater._handleSuccess({msg: "Boo. I've changed."});

            // Verify that both requests were issued.
            this.wait(function() {
                Y.Mock.verify(this.lp_client_mock);
            }, 5);

        }, 5);
    },

    test_actual_interval_doubled_if_request_too_long: function() {
        // The actual polling interval is doubled if the elapsed time
        // for the previous request was greater than the
        // long_processing_time attribute.
        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater, this.config);

        // Wait 5ms just to ensure that the DynamicDomUpdater finishes
        // its initialization.
        this.wait(function() {
            // Before calling the success handler, ensure that the
            // elapsed time will be evaluated as greater than the
            // long_processing_time defined in the config.
            this.eg_div.updater._request_start = new Date().getTime() - 11;
            this.eg_div.updater._handleSuccess({msg: "Boo. I've changed."});

            // The actual interval should have doubled from 1ms to 2ms.
            Assert.areEqual(
                2,
                this.eg_div.updater._actual_interval,
                "Poll interval doubled if request takes too long.");

        }, 5);
    },

    test_actual_interval_unchanged_if_request_normal: function() {
        // The actual polling interval remains unchanged if the elapsed time
        // for the previous request was within the short/long processing
        // times.
        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater, this.config);

        // Wait 5ms just to ensure that the DynamicDomUpdater finishes
        // its initialization.
        this.wait(function() {
            // Before calling the success handler, ensure that the
            // elapsed time will be evaluated as greater than the
            // short_processing_time but less than the long_processing_time
            // defined in the config.
            this.eg_div.updater._request_start = new Date().getTime() - 7;
            this.eg_div.updater._handleSuccess({msg: "Boo. I've changed."});

            // The actual interval is unchanged.
            Assert.areEqual(
                1,
                this.eg_div.updater._actual_interval,
                "Poll interval unchanged if request is timely.");

        }, 5);
    },

    test_actual_interval_halved_if_request_is_quick: function() {
        // The actual polling interval is halved if the elapsed time
        // for the previous request was less than the short_processing_time

        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater, this.config);

        // Wait 5ms just to ensure that the DynamicDomUpdater finishes
        // its initialization.
        this.wait(function() {
            // Before calling the success handler, ensure that the
            // elapsed time will be evaluated as less than the
            // short_processing_time defined in the config.
            this.eg_div.updater._request_start = new Date().getTime();

            // Ensure the current actual polling time is more than double the
            // requested interval.
            this.eg_div.updater._actual_interval = 16;

            this.eg_div.updater._handleSuccess({msg: "Boo. I've changed."});

            // The actual interval is unchanged.
            Assert.areEqual(
                8,
                this.eg_div.updater._actual_interval,
                "Poll interval is halved if request is faster than " +
                "expected.");

        }, 5);
    },

    test_actual_never_less_than_original_interval: function() {
        // Even if the processing time is quick, the actual interval
        // is never smaller than the interval set in the configuration.

        this.eg_div.plug(
            Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater, this.config);

        // Wait 5ms just to ensure that the DynamicDomUpdater finishes
        // its initialization.
        this.wait(function() {
            // Before calling the success handler, ensure that the
            // elapsed time will be evaluated as less than the
            // short_processing_time defined in the config.
            this.eg_div.updater._request_start = new Date().getTime();

            // Ensure the current actual polling time is more than double the
            // requested interval.
            this.eg_div.updater._actual_interval = 16;

            // Ensure that the configuration interval is greater than 8:
            this.eg_div.updater.set('interval', 10);

            this.eg_div.updater._handleSuccess({msg: "Boo. I've changed."});

            // The actual interval is unchanged.
            Assert.areEqual(
                10,
                this.eg_div.updater._actual_interval,
                "Actual interval never goes below config interval.");

        }, 5);
    }

}));

    Y.Test.Runner.on('complete', function(data) {
        window.status = '::::' + JSON.stringify(data);
    });
    Y.Test.Runner.add(suite);

    var yconsole = new Y.Console({
        newestOnTop: false
    });
    yconsole.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });

});
