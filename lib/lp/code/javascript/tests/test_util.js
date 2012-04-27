/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI().use('test', 'console', 'node-event-simulate', 'lp.testing.runner',
          'lp.code.util', function(Y) {

var suite = new Y.Test.Suite("lp.code.util Tests");
var module = Y.lp.code.util;


suite.add(new Y.Test.Case({
    name: "lp.code.util",

    setUp: function() {
        this.fixture = Y.one("#fixture");
        this.listener = {event_fired: false};
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

    _add_submit_listener: function() {
        // prevent submission when the form's method is directly invoked
        // and record that the methods was called.
        var listener = this.listener;
        Y.one('#filter_form').submit = function(e) {
            listener.event_fired = true;
            e.halt();
            };
    },

    test_hookUpDailyBuildsFilterSubmission: function() {
        this._setup_fixture('#daily-builds-form');
        module.hookUpDailyBuildsFilterSubmission();
        this._add_submit_listener();
        Y.one('[id=field.when_completed_filter]').simulate('change');
        Y.Assert.isTrue(this.listener.event_fired);
        Y.Assert.isTrue(
            Y.one('#filter_form_submit').hasClass('unseen'));
    },

    test_hookUpBranchFilterSubmission: function() {
        this._setup_fixture('#branch-listing-form');
        module.hookUpBranchFilterSubmission();
        this._add_submit_listener();
        Y.one('[id=field.lifecycle]').simulate('change');
        Y.Assert.isTrue(this.listener.event_fired);
        this.listener.event_fired = false;
        Y.one('[id=field.sort_by]').simulate('change');
        Y.Assert.isTrue(this.listener.event_fired);
        Y.Assert.isTrue(
            Y.one('#filter_form_submit').hasClass('unseen'));
    },

    test_hookUpMergeProposalFilterSubmission: function() {
        this._setup_fixture('#merge-proposal-form');
        module.hookUpMergeProposalFilterSubmission();
        this._add_submit_listener();
        Y.one('[id=field.status]').simulate('change');
        Y.Assert.isTrue(this.listener.event_fired);
        Y.Assert.isTrue(
            Y.one('#filter_form_submit').hasClass('unseen'));
    }
}));

Y.lp.testing.Runner.run(suite);

});
