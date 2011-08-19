/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('test', 'console', 'node-event-simulate',
          'lp.testing.iorecorder', 'lp.testing.runner',
          'lp.code.requestbuild_overlay', function(Y) {

var suite = new Y.Test.Suite("lp.code.requestbuild_overlay Tests");

var module = Y.lp.code.requestbuild_overlay;

var build_targets_markup = '<table>' +
    '<tr class="package-build" id="build-1"></tr>' +
    '<tr class="package-build" id="build-2"></tr>' +
    '</table>';

suite.add(new Y.Test.Case({
    name: "lp.code.requestbuild_overlay",

    setUp: function() {
        LP.cache['context'] = {
            web_link: "http://code.launchpad.dev/~foobar/myrecipe"};
    },

    test_requestbuild: function() {
        var recorder = new Y.lp.testing.iorecorder.IORecorder();
        var build_now_link = Y.one('#request-daily-build');
        build_now_link.removeClass('unseen');
        module.connect_requestdailybuild(
            {io: Y.bind(recorder.do_io, recorder)});
        build_now_link.simulate('click');
        
        Y.Assert.areEqual(1, recorder.requests.length);
        var request = recorder.requests[0];
        request.success(
            build_targets_markup,  {'Content-Type': 'application/xhtml'});
        var build_targets = Y.one("#builds-target");
        Y.log(build_targets.get('innerHTML'));
    },



}));

Y.lp.testing.Runner.run(suite);

});
