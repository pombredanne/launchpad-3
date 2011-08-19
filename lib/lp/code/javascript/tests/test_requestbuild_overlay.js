/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('test', 'console', 'node-event-simulate',
          'lp.testing.iorecorder', 'lp.testing.runner',
          'lp.code.requestbuild_overlay', function(Y) {

var suite = new Y.Test.Suite("lp.code.requestbuild_overlay Tests");

var module = Y.lp.code.requestbuild_overlay;

var builds_target_markup = '<table>' +
    '<tr class="package-build" id="build-1"></tr>' +
    '<tr class="package-build" id="build-2"></tr>' +
    '</table>';

suite.add(new Y.Test.Case({
    name: "lp.code.requestbuild_overlay",

    setUp: function() {
        LP.cache['context'] = {
            web_link: "http://code.launchpad.dev/~foobar/myrecipe"};
        // Prepare testbed.
        var testbed = Y.one("#testbed").set('innerHTML', '');
        testbed.append(
            Y.Node.create('<a></a>')
                .set('id', 'request-daily-build')
                .set('href', '#')
                .addClass('unseen')
                .set('text', 'Build now')
        ).append(
            Y.Node.create('<div></div>')
                .set('id', 'builds-target')
        );
    },

    test_requestbuild_success: function() {
        var recorder = new Y.lp.testing.iorecorder.IORecorder();
        var build_now_link = Y.one('#request-daily-build');
        build_now_link.removeClass('unseen');
        module.connect_requestdailybuild(
            {io: Y.bind(recorder.do_io, recorder)});
        build_now_link.simulate('click');
        
        Y.Assert.areSame(1, recorder.requests.length);
        var request = recorder.requests[0];
        request.success(
            builds_target_markup,  {'Content-Type': 'application/xhtml'});

        // The markup has been inserted.
        Y.Assert.areSame(
            2, Y.one("#builds-target").all('.package-build').size());
        // The message is being displayed as informational.
        var info = Y.one("#new-builds-info");
        Y.Assert.isTrue(info.hasClass('build-informational'));
        Y.Assert.areSame(
            "2 new recipe builds have been queued.Dismiss",
            info.get('text'));
        // The message can be dismissed.
        info.one('a').simulate('click');
        Y.Assert.areSame('none', info.getStyle('display'));
        // The build now button is hidden.
        Y.Assert.isTrue(build_now_link.hasClass('unseen'));
    },


    test_requestbuild_failure_503: function() {
        var recorder = new Y.lp.testing.iorecorder.IORecorder();
        var build_now_link = Y.one('#request-daily-build');
        build_now_link.removeClass('unseen');
        module.connect_requestdailybuild(
            {io: Y.bind(recorder.do_io, recorder)});
        build_now_link.simulate('click');
        
        Y.Assert.areSame(1, recorder.requests.length);
        var request = recorder.requests[0];
        request.respond(503, '',  {});

        // No build targets.
        Y.Assert.areSame(
            0, Y.one("#builds-target").all('.package-build').size());
        // The message is being displayed as an error.
        var error = Y.one("#new-builds-info");
        Y.Assert.isTrue(error.hasClass('build-error'));
        Y.Assert.areSame(
            "Timeout error, please try again in a few minutes.Dismiss",
            error.get('text'));
        // The message can be dismissed.
        error.one('a').simulate('click');
        Y.Assert.areSame('none', error.getStyle('display'));
        // The build now button stays visible.
        Y.Assert.isFalse(build_now_link.hasClass('unseen'));
    },



}));

Y.lp.testing.Runner.run(suite);

});
