/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI().use('lp.testing.runner', 'test', 'console', 'node',
          'lp.app.privacy', 'node-event-simulate', function(Y) {

    var suite = new Y.Test.Suite("lp.app.privacy Tests");

    suite.add(new Y.Test.Case({
        name: 'privacy',

        setUp: function() { },

    Y.lp.testing.Runner.run(suite);

});

