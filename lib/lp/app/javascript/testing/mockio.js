/* Copyright (c) 2009-2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.testing.mockio', function(Y) {
    /**
     * A utility module for use in YUI unit-tests with a helper for mocking Y.io.
     *
     * @module lp.testing.mockio
     */
    var namespace =  Y.namespace("lp.testing.mockio");

    var MockHttpResponse = function(config) {
        if (config === undefined) {
            config = {};
        }
        if (config.status !== undefined) {
            this.status = config.status;
        } else {
            this.status = 200;
        }
        if (config.statusText !== undefined) {
            this.statusText = config.statusText;
        } else {
            if (this.isFailure()) {
                this.statusText = "Internal Server Error";
            } else {
                this.statusText = "OK";
            }
        }
        if (config.responseText !== undefined) {
            this.responseText = config.responseText;
        } else {
            this.responseText = '[]';
        }
        if (config.responseHeaders !== undefined) {
            this.responseHeaders = config.responseHeaders;
        } else {
            this.responseHeaders = {};
        }
    }

    MockHttpResponse.prototype = {
        isFailure: function () {
            return this.status >= 500;
        },

        setResponseHeader: function (header, value) {
            this.responseHeaders[header] = value;
        },

        getResponseHeader: function(header) {
            return this.responseHeaders[header];
        }
    };
    namespace.MockHttpResponse = MockHttpResponse;
    
    var MockIo = function() {
        this.uri = null;
        this.cfg = null;
    };
    
    /* Save the Y.io() arguments. */
    MockIo.prototype.io = function(url, config) {
        this.url = url;
        this.config = config;
        return this;  // Usually this isn't used, except for logging.
    };
    
    /* Simulate the Xhr request/response cycle. */
    MockIo.prototype.respond = function(response_config) {
        var context = this.config.context || this,
            args = this.config.arguments,
            tId = 'mockTId',
            response = new MockHttpResponse(response_config);
    
        // See the Y.io utility documentation for the signatures.
        if (this.config.on.start !== undefined) {
            this.config.on.start.call(context, tId, args);
        }
        if (this.config.on.complete !== undefined) {
            this.config.on.complete.call(context, tId, response, args);
        }
        if (this.config.on.success !== undefined && !response.isFailure()) {
            this.config.on.success.call(context, tId, response, args);
        }
        if (this.config.on.failure !== undefined && response.isFailure()) {
            this.config.on.failure.call(context, tId, response, args);
        }
    };
    
    /* Make a successful XHR response object. */
    MockIo.makeXhrSuccessResponse = function(responseText) {
        var text = responseText || "";
        return {
            status: 200,
            statusText: "OK",
            responseText: text
        };
    };
    
    /* Make a failed XHR response object. */
    MockIo.makeXhrFailureResponse = function(responseText) {
        var text = responseText || "";
        return {
            status: 500,
            statusText: "Internal Server Error",
            responseText: text
        };
    };

namespace.MockIo = MockIo;

}, '0.1', {});
