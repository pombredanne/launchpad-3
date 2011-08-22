/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.testing.iorecorder', function(Y) {
    var namespace = Y.namespace("lp.testing.iorecorder");

    function MockHttpResponse (status) {
        this.status = status;
        this.responseText = '[]';
        this.responseHeaders = {};
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


    function IORecorderRequest(url, config){
        this.url = url;
        this.config = config;
        this.response = null;
    }


    IORecorderRequest.prototype.respond = function(status, value, headers){
        this.response = new MockHttpResponse(status);
        this.response.setResponseHeader(
            'Content-Type', headers['Content-Type']);
        this.response.responseText = value;
        var callback;
        if (status === 200) {
            callback = this.config.on.success;
        } else {
            callback = this.config.on.failure;
        }
        callback(null, this.response, this.config['arguments']);
    };


    IORecorderRequest.prototype.success = function(value, headers){
        this.respond(200, value, headers);
    };


    function IORecorder(){
        this.requests = [];
    }


    IORecorder.prototype.do_io = function(url, config){
        this.requests.push(new IORecorderRequest(url, config));
    };
    namespace.IORecorder = IORecorder;
}, '0.1', {});
