/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI().use('test', 'console', 'node-event-simulate', 'lp.testing.runner',
          'lp.code.util', function(Y) {

var suite = new Y.Test.Suite("lp.code.util Tests");
var module = Y.lp.code.util;


suite.add(new Y.Test.Case({
    name: "lp.code.util",

    setUp: function() {
        this.fixture = Y.one("#fixture");
    },

    tearDown: function () {
        if (this.fixture !== null) {
            this.fixture.empty(true);
        }
        delete this.fixture;
    },

    _setup_fixture: function(template_selector) {
        var template =Y.one(template_selector).getContent();
        var test_node = Y.Node.create(template);
        this.fixture.append(test_node);
    },

    test_hookUpDailyBuildsFilterSubmission: function() {
        this._setup_fixture('#daily-builds-form');
        module.hookUpDailyBuildsFilterSubmission();
        var event_fired = false;
        var form = Y.one('[id=filter_form]');
        // prevent submission when the form's method is directly invoked.
        form.submit = function(e) {
            event_fired = true;
            e.halt(true);
            };
        var field = Y.one('[id=field.when_completed_filter]');
        field.simulate('change');
        Y.Assert.isTrue(event_fired);
    }
}));

Y.lp.testing.Runner.run(suite);

});
