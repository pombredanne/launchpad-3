/* Copyright (c) 2009-2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.testing.mockio', function(Y) {
    /**
     * A utility module for use in YUI unit-tests with a helper for mocking Y.io.
     *
     * @module lp.testing.mockio
     */
    var namespace =  Y.namespace("lp.testing.mockio");

    var _is_failure(status) {
        return status >= 500;
    }
    
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
            if _is_failure(this.status) {
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
    MockIo.prototype.io = function(uri, cfg) {
        this.uri = uri;
        this.cfg = cfg;
        return this;  // Usually this isn't used, except for logging.
    };
    
    /* Simulate the Xhr request/response cycle. */
    MockIo.prototype.simulateXhr = function(response, is_failure) {
        var cfg = this.cfg;
        var context = cfg.context || this;
        var args = cfg.arguments;
        var tId = 'mockTId';
        if (!response) {
            response = {};
        }
    
        // See the Y.io utility documentation for the signatures.
        if (cfg.on.start) {
            cfg.on.start.call(context, tId, args);
        }
        if (cfg.on.complete) {
            cfg.on.complete.call(context, tId, response, args);
        }
        if (cfg.on.success && !is_failure) {
            cfg.on.success.call(context, tId, response, args);
        }
        if (cfg.on.failure && is_failure) {
            cfg.on.failure.call(context, tId, response, args);
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
