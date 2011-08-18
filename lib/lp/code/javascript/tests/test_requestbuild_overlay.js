/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'lp.testing.iorecorder', 'test', 'console',
          'lp.client', 'lp.code.requestbuild_overlay', function(Y) {

var suite = new Y.Test.Suite("lp.code.requestbuild_overlay Tests");

var module = Y.lp.code.requestbuild_overlay;

var patch_handler = function(handler) {
    handler.showError_count = 0;
    handler.showError = function() {
        handler.showError_count += 1;
    };
    handler.clearProgressUI_count = 0;
    handler.clearProgressUI = function() {
        handler.clearProgressUI_count += 1;
    };
};

suite.add(new Y.Test.Case({
    name: "lp.code.requestbuild_overlay.RequestResponseHandler",

    setUp: function() {
    },

    test_success_handler: function() {
        var handler = new module.RequestResponseHandler();
        var callback_count = 0;
        patch_handler(handler);

        var success_handler = handler.getSuccessHandler(function() {
           callback_count += 1;
        });
        success_handler();

        Y.Assert.areEqual(1, callback_count);
        Y.Assert.areEqual(1, handler.clearProgressUI_count);
        Y.Assert.areEqual(0, handler.showError_count);        
    },


}));

Y.lp.testing.Runner.run(suite);

});
