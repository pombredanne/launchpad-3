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

        makeExpanderHooks: function () {
            var root = Y.Node.create('<div></div>');
            root.appendChild(Y.Node.create('<div class="icon"></div>'));
            root.appendChild(Y.Node.create('<div class="content"></div>'));
            return root;
        },

        test_setUp_creates_collapsed_icon_by_default: function () {
            var root = this.makeExpanderHooks();
            var icon = root.one('.icon');
            new module.Expander(
                root.one('.icon'), root.one('.content')).setUp();
            Y.Assert.isTrue(icon.hasClass('sprite'));
            Y.Assert.isTrue(icon.hasClass('treeCollapsed'));
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

