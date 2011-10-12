/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI().use('lp.testing.runner', 'lp.testing.mockio', 'base', 'test', 'console',
          'node', 'node-event-simulate', 'lp.app.batchnavigator',
    function(Y) {

    var suite = new Y.Test.Suite("lp.app.batchnavigator Tests");
    var module = Y.lp.app.batchnavigator;

    var BatchNavigatorTestMixin = {

        setUp: function() {
            this.findRootTag().setContent('');
        },

        tearDown: function() {
            if (this.navigator !== undefined) {
                delete this.navigator;
            }
        },

        findRootTag: function() {
            return Y.one('.test-hook');
        },

        makeNode: function(node_type, id, css_class) {
            var node = Y.Node.create(
                    Y.Lang.substitute(
                            '<{node_type}></{node_type}>',
                            {node_type: node_type}));
            if (id !== undefined) {
                node.setAttribute('id', id);
            }
            if (css_class !== undefined) {
                node.addClass(css_class);
            }
            return node;
        },

        makeNavLink: function(cell, link_type, active) {
            if (active) {
                cell.appendChild(
                        this.makeNode('a', undefined, link_type))
                    .set('href', 'http://' + link_type)
                    .setContent(link_type);
            } else {
                cell.appendChild(this.makeNode('span', undefined, link_type))
                    .addClass('inactive')
                    .setContent(link_type);
            }
        },

        makeNavigatorHooks: function(args) {
            if (!Y.Lang.isValue(args)) {
                args = {};
            }
            var root = this.findRootTag();
            var batch_links = this.makeNode('div', 'batch-links');
            var table = batch_links.appendChild(this.makeNode(
                    'table', undefined, 'upper-batch-nav'));
            var row = table.appendChild(this.makeNode('tr'));
            var cell = row.appendChild(
                    this.makeNode('td', undefined, 'batch-navigation-links'));
            this.makeNavLink(cell, 'first', false);
            this.makeNavLink(cell, 'previous', false);
            this.makeNavLink(cell, 'next', true);
            this.makeNavLink(cell, 'last', true);
            root.appendChild(batch_links);
            return root;
        },

        makeNavigator: function(root, args) {
            if (!Y.Lang.isValue(args)) {
                args = {};
            }
            if (root === undefined) {
                root = this.makeNavigatorHooks();
            }
            var extra_config = args.config;
            if (extra_config === undefined) {
                extra_config = {};
            }
            var config = Y.mix(
                extra_config, {contentBox: root});
            var navigator = new module.BatchNavigatorHooks(
                config, args.io_provider);
            this.navigator = navigator;
            return navigator;
        }
    };

    suite.add(new Y.Test.Case(
        Y.merge(BatchNavigatorTestMixin, {

        name: 'batchnavigator',

        test_navigator_construction: function() {
            this.makeNavigator(this.makeNavigatorHooks());
        },

        _test_enabled_link_click: function(link_type) {
            var mockio = new Y.lp.testing.mockio.MockIo();
            this.makeNavigator(
                this.makeNavigatorHooks(),
                {io_provider: mockio,
                 config: {batch_request_value: 'foobar'}});
            Y.one('#batch-links a.'+link_type).simulate('click');
            mockio.success({
                responseText: '<p>Batch content</p>',
                responseHeaders: {'Content-Type': 'text/html'}});

            // The URL has the batch_request parameter added.
            Y.Assert.areEqual(
                'http://'+link_type + '/&batch_request=foobar',
                mockio.last_request.url);
            // The content is rendered.
            Y.Assert.areEqual(
                '<p>Batch content</p>',
                this.findRootTag().getContent());
        },

        // The following link tests check that the enabled navigation links
        // work as expected. We test the 'next' and 'last' links. The 'first'
        // and 'previous' links are not enabled.
            
        test_next_link: function() {
            this._test_enabled_link_click('next');
        },

        test_last_link: function() {
            this._test_enabled_link_click('last');
        },

        test_show_spinner: function() {
            var navigator = this.makeNavigator(this.makeNavigatorHooks());
            navigator.showSpinner();
            Y.Assert.isFalse(navigator.links_active);
            Y.Assert.isTrue(
                this.findRootTag().all('.spinner').size() > 0);
            this.findRootTag().all('a', function(link) {
                Y.Assert.isTrue(link.hasClass('inactive'));
            });
        },

        test_hide_spinner: function() {
            var navigator = this.makeNavigator(this.makeNavigatorHooks());
            navigator.showSpinner();
            navigator.hideSpinner();
            Y.Assert.isTrue(navigator.links_active);
            Y.Assert.isFalse(
                this.findRootTag().all('.spinner').size() > 0);
            this.findRootTag().all('a', function(link) {
                Y.Assert.isFalse(link.hasClass('inactive'));
            });
        }
    })));

    Y.lp.testing.Runner.run(suite);

});

