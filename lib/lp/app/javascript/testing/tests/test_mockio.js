/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('test', 'console', 'node-event-simulate',
          'lp.testing.mockio', 'lp.testing.runner', function(Y) {

var suite = new Y.Test.Suite("lp.testing.mockio Tests");

var module = Y.lp.testing.mockio;

var make_call_recorder = function() {
    var recorder = function() {
        this.call_count += 1;
        this.arguments = arguments;
    }
    recorder.call_count = 0;
    recorder.arguments = null;
    return recorder;
};

suite.add(new Y.Test.Case({
    name: "lp.testing.mokio",

    test_url: "https://launchpad.dev/test/url",
    test_config: {
        on: {
            start: make_call_recorder(),
            complete: make_call_recorder(),
            success: make_call_recorder(),
            failure: make_call_recorder()
        },
        context:  {marker: "context"},
        arguments: ["arguments"]
    },
    
    setUp: function() {
    },

    _make_mockio: function() {
        var mockio = new module.MockIO();
        mockio.io(this.test_url, this.test_config);
        return mockio;
    },
    
    test_success: function() {
        // The success handler is called on success.
        var mockio = this._make_mockio();
        mockio.respond({status: 200});
        Y.Assert.areEqual(1, test_config.on.start.call_count)
        Y.Assert.areEqual(1, test_config.on.complete.call_count)
        Y.Assert.areEqual(1, test_config.on.success.call_count)
        Y.Assert.areEqual(0, test_config.on.failure.call_count)
    },
    
    test_failure: function() {
        // The failure handler is called on failure.
        var mockio = this._make_mockio();
        mockio.respond({status: 500});
        Y.Assert.areEqual(1, test_config.on.start.call_count)
        Y.Assert.areEqual(1, test_config.on.complete.call_count)
        Y.Assert.areEqual(0, test_config.on.success.call_count)
        Y.Assert.areEqual(1, test_config.on.failure.call_count)
    },
    
    test_status: function() {
        // The status is passed to the handler.
        var mockio = this._make_mockio();
        var expected_status = 503;
        mockio.respond({status: expected_status});
        var status = test_config.on.failure.arguments[2].status;
        Y.Assert.areEqual(expected_status, response_status);
    },
    
    test_statusText: function() {
        // The statusText is passed to the handler.
        var mockio = this._make_mockio();
        var expected_status_text = "All is well";
        mockio.respond({statusText: expected_status_text});
        var status_text = test_config.on.success.arguments[2].responseText;
        Y.Assert.areEqual(expected_status_text, status_text);
    },
    
    test_responseText: function() {
        // The responseText is passed to the handler.
        var mockio = this._make_mockio();
        var expected_response_text = "myresponse";
        mockio.respond({responseText: expected_response_text});
        var response_text = test_config.on.success.arguments[2].responseText;
        Y.Assert.areEqual(expected_response_text, response_text);
    }
}));

Y.lp.testing.Runner.run(suite);

});
