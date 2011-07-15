/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.testing.iorecorder', function(Y) {
    namespace = Y.namespace("lp.testing.iorecorder");
    function MockHttpResponse () {
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
    namespace.MockHttpResponse = MockHttpResponse


    function IORecorderRequest(url, config){
        this.url = url;
        this.config = config;
        this.response = null;
    }


    IORecorderRequest.prototype.success = function(value, headers){
        this.response = new MockHttpResponse();
        this.response.setResponseHeader('Content-Type', headers['Content-Type']);
        this.response.responseText = value;
        this.config.on.success(null, this.response, this.config['arguments']);
    };


    function IORecorder(){
        this.requests = [];
    }


    IORecorder.prototype.do_io = function(url, config){
        this.requests.push(new IORecorderRequest(url, config));
    };
    namespace.IORecorder = IORecorder
}, '0.1', {});
