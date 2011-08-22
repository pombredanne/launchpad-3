/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('test', 'console', 'node-event-simulate',
          'lp.testing.mockio', 'lp.testing.runner', function(Y) {

var suite = new Y.Test.Suite("lp.testing.mockio Tests");

var module = Y.lp.testing.mockio;

var make_call_recorder = function() {
    var recorder;
    recorder = function() {
        recorder.call_count += 1;
        recorder.arguments = arguments;
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
        var mockio = new module.MockIo();
        mockio.io(this.test_url, this.test_config);
        return mockio;
    },

    test_success: function() {
        // The success handler is called on success.
        var mockio = this._make_mockio();
        mockio.respond({status: 200});
        Y.Assert.areEqual(1, this.test_config.on.start.call_count)
        Y.Assert.areEqual(1, this.test_config.on.complete.call_count)
        Y.Assert.areEqual(1, this.test_config.on.success.call_count)
        Y.Assert.areEqual(0, this.test_config.on.failure.call_count)
    },

    test_failure: function() {
        // The failure handler is called on failure.
        var mockio = this._make_mockio();
        mockio.respond({status: 500});
        Y.Assert.areEqual(1, this.test_config.on.start.call_count)
        Y.Assert.areEqual(1, this.test_config.on.complete.call_count)
        Y.Assert.areEqual(0, this.test_config.on.success.call_count)
        Y.Assert.areEqual(1, this.test_config.on.failure.call_count)
    },

    test_multiple_requests: function() {
        // Multiple requests are stored.
        var mockio = new module.MockIo();
        mockio.io(this.test_url, this.test_config);
        mockio.io(this.test_url, this.test_config);
        Y.Assert.areEqual(2, mockio.requests.length);
    },

    test_last_request: function() {
        // The last request is available through last_request.
        var mockio = new module.MockIo();
        mockio.io("Request 1", this.test_config);
        mockio.io("Request 2", this.test_config);
        Y.Assert.areEqual("Request 2", mockio.last_request.url);
    },

    test_status: function() {
        // The status is passed to the handler.
        var mockio = this._make_mockio();
        var expected_status = 503;
        mockio.respond({status: expected_status});
        Y.Assert.areEqual(
            expected_status,
            this.test_config.on.failure.arguments[2].status);
    },

    test_statusText: function() {
        // The statusText is passed to the handler.
        var mockio = this._make_mockio();
        var expected_status_text = "All is well";
        mockio.respond({statusText: expected_status_text});
        Y.Assert.areEqual(
            expected_status_text,
            this.test_config.on.success.arguments[2].statusText);
    },

    test_responseText: function() {
        // The responseText is passed to the handler.
        var mockio = this._make_mockio();
        var expected_response_text = "myresponse";
        mockio.respond({responseText: expected_response_text});
        Y.Assert.areEqual(
            expected_response_text,
            this.test_config.on.success.arguments[2].responseText);
    },

    test_responseHeader: function() {
        // A response header is passed to the handler.
        var mockio = this._make_mockio();
        var expected_header_key = "X-My-Header",
            expected_header_val = "MyHeaderValue";
        mockio.respond(
            {responseHeaders: {expected_header_key: expected_header_val}});
        var headers = this.test_config.on.
                success.arguments[2].responseHeaders;
        Y.Assert.areEqual(expected_header_val, headers[expected_header_key]);
    }
}));

Y.lp.testing.Runner.run(suite);

});
