/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('test', 'console', 'node-event-simulate',
          'lp.testing.mockio', 'lp.testing.runner', function(Y) {

var suite = new Y.Test.Suite("lp.testing.mockio Tests");

var module = Y.lp.testing.mockio;

var make_call_recorder = function() {
    var recorder;
    recorder = function() {
        recorder.call_count += 1;
        recorder.args = arguments;
    };
    recorder.call_count = 0;
    recorder.args = null;
    return recorder;
};

suite.add(new Y.Test.Case({
    name: "lp.testing.mokio.MockIo",

    test_url: "https://launchpad.dev/test/url",

    setUp: function() {
        // Initialize call_count on recorders.
        this.test_config = {
            on: {
                start: make_call_recorder(),
                complete: make_call_recorder(),
                success: make_call_recorder(),
                failure: make_call_recorder()
            },
            context:  {marker: "context"},
            'arguments': ["arguments"]
        };
    },

    _make_mockio: function() {
        var mockio = new module.MockIo();
        mockio.io(this.test_url, this.test_config);
        return mockio;
    },

    test_respond_success: function() {
        // The success handler is called on success.
        var mockio = this._make_mockio();
        mockio.respond({status: 200});
        Y.Assert.areEqual(1, this.test_config.on.start.call_count);
        Y.Assert.areEqual(1, this.test_config.on.complete.call_count);
        Y.Assert.areEqual(1, this.test_config.on.success.call_count);
        Y.Assert.areEqual(0, this.test_config.on.failure.call_count);
    },

    test_respond_failure: function() {
        // The failure handler is called on failure.
        var mockio = this._make_mockio();
        mockio.respond({status: 500});
        Y.Assert.areEqual(1, this.test_config.on.start.call_count);
        Y.Assert.areEqual(1, this.test_config.on.complete.call_count);
        Y.Assert.areEqual(0, this.test_config.on.success.call_count);
        Y.Assert.areEqual(1, this.test_config.on.failure.call_count);
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
            expected_status, this.test_config.on.failure.args[1].status);
    },

    test_statusText: function() {
        // The statusText is passed to the handler.
        var mockio = this._make_mockio();
        var expected_status_text = "All is well";
        mockio.respond({statusText: expected_status_text});
        Y.Assert.areEqual(
            expected_status_text,
            this.test_config.on.success.args[1].statusText);
    },

    test_responseText: function() {
        // The responseText is passed to the handler.
        var mockio = this._make_mockio();
        var expected_response_text = "myresponse";
        mockio.respond({responseText: expected_response_text});
        Y.Assert.areEqual(
            expected_response_text,
            this.test_config.on.success.args[1].responseText);
    },

    test_responseHeader: function() {
        // A response header is passed to the handler.
        var mockio = this._make_mockio();
        var response = new Y.lp.testing.mockio.MockHttpResponse();
        var expected_header_key = "X-My-Header",
            expected_header_val = "MyHeaderValue",
            response_headers = {};
        response.setResponseHeader(expected_header_key,  expected_header_val);
        mockio.respond(response);
        var headers = this.test_config.on.success.args[1].responseHeaders;
        Y.Assert.areEqual(expected_header_val, headers[expected_header_key]);
    },

    test_success_helper: function() {
        // The success helper creates a successful response.
        var mockio = this._make_mockio(),
            response_text = "Success!";
        mockio.success({responseText: response_text});
        Y.Assert.areEqual(1, this.test_config.on.success.call_count);
        Y.Assert.areEqual(0, this.test_config.on.failure.call_count);
        Y.Assert.areEqual(
            response_text, mockio.last_request.response.responseText);
    },

    test_success_helper__own_status: function() {
        // The failure can define its own non-4xx or non-5xx status.
        var mockio = this._make_mockio(),
            status = 302;
        mockio.success({status: status});
        Y.Assert.areEqual(1, this.test_config.on.success.call_count);
        Y.Assert.areEqual(0, this.test_config.on.failure.call_count);
        Y.Assert.areEqual(status, mockio.last_request.response.status);
    },

    test_success_helper__status_override: function() {
        // A status that is 4xx or 5xx is overridden to be 200.
        // This is to guard against foot shooting.
        var mockio = this._make_mockio(),
            own_status = 500,
            real_status = 200;
        mockio.success({status: own_status});
        Y.Assert.areEqual(1, this.test_config.on.success.call_count);
        Y.Assert.areEqual(0, this.test_config.on.failure.call_count);
        Y.Assert.areEqual(real_status, mockio.last_request.response.status);
    },

    test_failure_helper: function() {
        // The failure helper creates a failed response.
        var mockio = this._make_mockio(),
            response_text = "Failure!";
        mockio.failure({responseText: response_text});
        Y.Assert.areEqual(0, this.test_config.on.success.call_count);
        Y.Assert.areEqual(1, this.test_config.on.failure.call_count);
        Y.Assert.areEqual(
            response_text, mockio.last_request.response.responseText);
    },

    test_failure_helper__own_status: function() {
        // The failure can define its own 4xx or 5xx status.
        var mockio = this._make_mockio(),
            status = 404;
        mockio.failure({status: status});
        Y.Assert.areEqual(0, this.test_config.on.success.call_count);
        Y.Assert.areEqual(1, this.test_config.on.failure.call_count);
        Y.Assert.areEqual(status, mockio.last_request.response.status);
    },

    test_failure_helper__status_override: function() {
        // A status that is not 4xx or 5xx is overridden to be 500.
        // This is to guard against foot shooting.
        var mockio = this._make_mockio(),
            own_status = 200,
            real_status = 500;
        mockio.failure({status: own_status});
        Y.Assert.areEqual(0, this.test_config.on.success.call_count);
        Y.Assert.areEqual(1, this.test_config.on.failure.call_count);
        Y.Assert.areEqual(real_status, mockio.last_request.response.status);
    }
}));

suite.add(new Y.Test.Case({
    name: "lp.testing.mokio.io_provider",

    setUp: function() {
    },

    test_io_provider__default: function() {
        var mockio,
            io_provider = module.io_provider(mockio);
        Y.Assert.areSame(Y, io_provider);
    },

    test_io_provider__mockio: function() {
        // If mockio is provided, it is picked as the io_provider.
        var mockio = new module.MockIo(),
            io_provider = module.io_provider(mockio);
        Y.Assert.areSame(mockio, io_provider);
    },

    test_io_provider_config__default: function() {
        // If no io_provider is configured, Y is the io_provider.
        var io_provider = module.io_provider_config({});
        Y.Assert.areSame(Y, io_provider);
    },

    test_io_provider_config__default_undefined: function() {
        // If no configuration is provided, Y is the io_provider.
        var io_provider = module.io_provider_config();
        Y.Assert.areSame(Y, io_provider);
    },

    test_io_provider_config__mockio: function() {
        // If io_provider is configured,  it is picked as the io_provider.
        var mockio = new module.MockIo(),
            io_provider = module.io_provider_config(
                {io_provider: mockio});
        Y.Assert.areSame(mockio, io_provider);
    },

    test_io_provider_config__different_key: function() {
        // The io_provider can be stored with a different key.
        var mockio = new module.MockIo(),
            io_provider = module.io_provider_config(
                {my_io: mockio}, 'my_io');
        Y.Assert.areSame(mockio, io_provider);
    }
}));


Y.lp.testing.Runner.run(suite);

});
