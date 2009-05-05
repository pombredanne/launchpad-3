/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../icing/yui/current/build/',
    filter: 'raw',
    combine: false
    }).use('yuitest', 'console', 'soyuz.dynamic_dom_updater', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("DynamicDomUpdater Tests");

suite.add(new Y.Test.Case({

    name: 'dom_updater',

    setUp: function() {
        this.eg_div = Y.Node.create(
            '<div>Default text to start with.</div>');
        this.config = {
            domUpdateFunction: function(node, data_object) {
                node.set('innerHTML', data_object.msg)
            }
        };
    },

    test_dom_updater_is_pluggable: function() {
        // Plugging the DomUpdater adds an 'updater' attribute.
        Assert.isUndefined(
            this.eg_div.updater,
            "Sanity check: initially there is no updater attribute.");

        this.eg_div.plug(Y.LP.DomUpdater, this.config);

        Assert.isNotUndefined(
            this.eg_div.updater,
            "After plugging, the object has an 'updater' attribute.");

        Assert.isInstanceOf(
            Y.LP.DomUpdater,
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

        this.eg_div.plug(Y.LP.DomUpdater, this.config);
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
                node.set('innerHTML', data_object.msg)
            },
            uri: 'http://example.com',
            api_method_name: 'my_method',
            interval: 1,
            lp_client: this.lp_client_mock
        };
    },

    test_dynamic_dom_updater_is_pluggable: function() {
        // Plugging the DomUpdater adds an 'updater' attribute.

        // We expect only one named_get call on the lp client
        Y.Mock.expect(this.lp_client_mock, {
            method: "named_get",
            args: ['http://example.com', 'my_method', Y.Mock.Value.Object],
            callCount: 1
        })

        Assert.isUndefined(
            this.eg_div.updater,
            "Sanity check: initially there is no updater attribute.");

        this.eg_div.plug(Y.LP.DynamicDomUpdater, this.config);

        Assert.isNotUndefined(
            this.eg_div.updater,
            "After plugging, the object has an 'updater' attribute.");

        Assert.isInstanceOf(
            Y.LP.DynamicDomUpdater,
            this.eg_div.updater,
            "DynamicDomUpdater was not plugged correctly.");
    },

    test_no_further_request_if_previous_response_not_received: function() {
        // Requests to the LP API should only be re-issued if a successful
        // response was received previously.

        // We expect only one named_get call on the lp client
        Y.Mock.expect(this.lp_client_mock, {
            method: "named_get",
            args: ['http://example.com', 'my_method', Y.Mock.Value.Object],
            callCount: 1
        })

        this.eg_div.plug(Y.LP.DynamicDomUpdater, this.config);

        // Verify that our expectation of only one named_get was met:
        this.wait(function() {
            Y.Mock.verify(this.lp_client_mock);
        }, 100);
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

        this.eg_div.plug(Y.LP.DynamicDomUpdater, this.config);

        // Wait 5ms and then simulate a successful response to the updater:
        this.wait(function() {
            this.eg_div.updater._handleSuccess({msg: "Boo. I've changed."});

            // Verify that both requests were issued.
            this.wait(function() {
                Y.Mock.verify(this.lp_client_mock);
            }, 100);

        }, 5);
    },

}));

Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
