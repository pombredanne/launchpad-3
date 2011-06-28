/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: false
    }).use('test', 'console', 'node', 'node-event-simulate',
           'lp.app.widgets.expander', function(Y) {

    var suite = new Y.Test.Suite("lp.app.widgets.expander Tests");
    var module = Y.lp.app.widgets.expander;

    suite.add(new Y.Test.Case({
        name: 'exandable',

        test_foo: function () {
            module.setupExpanders(".expandable-item");
        }
    }));

    var handle_complete = function(data) {
        window.status = '::::' + JSON.stringify(data);
    };
    Y.Test.Runner.on('complete', handle_complete);
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {Y.Test.Runner.run();});
});

