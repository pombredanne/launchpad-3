/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: false
}).use('base', 'test', 'console', 'node', 'node-event-simulate',
       'lp.app.widgets.expander', function(Y) {

    function FakeAnim(config) {
        FakeAnim.superclass.constructor.apply(this, arguments);
        this.call_stack = [];
   }

    FakeAnim.ATTRS = {
        running: { value: false },
        reverse: { value: false },
        to: { value: {} },
        from: { value: {} }
    };

    Y.extend(FakeAnim, Y.Base, {
        stop: function() {
            this.call_stack.push('stop');
            this.set('running', false);
        },

        run: function() {
            this.call_stack.push('run');
            this.set('running', true);
        }
    });

    var suite = new Y.Test.Suite("lp.app.widgets.expander Tests");
    var module = Y.lp.app.widgets.expander;

    suite.add(new Y.Test.Case({
        name: 'expandable',

        setUp: function() {
            this.findTestHookTag().setContent('');
        },

        findTestHookTag: function() {
            return Y.one('.test-hook');
        },

        makeNode: function(css_class) {
            var node = Y.Node.create('<div></div>');
            if (css_class !== undefined) {
                node.addClass(css_class);
            }
            return node;
        },

        makeExpanderHooks: function(args) {
            if (!Y.Lang.isValue(args)) {
                args = {};
            }
            var root = this.makeNode();
            var hook = root.appendChild(this.makeNode('hook'));
            var icon = hook.appendChild(this.makeNode('icon'));
            var content = hook.appendChild(this.makeNode('content'));
            if (args.expanded) {
                content.addClass('expanded');
            }
            return root;
        },

        makeExpander: function(root, args) {
            if (!Y.Lang.isValue(args)) {
                args = {};
            }
            if (root === undefined) {
                root = this.makeExpanderHooks();
            }
            return new module.Expander(
                root.one('.icon'), root.one('.content'), args.config).setUp();
        },

        test_separate_animate_node: function() {
            var icon = Y.Node.create('<td></td>'),
                content = Y.Node.create('<td></td>'),
                animate = Y.Node.create('<div></div>');
            var expander = new module.Expander(icon, content,
                                               { animate_node: animate });
            Y.Assert.areSame(content, expander.content_node);
            Y.Assert.areSame(animate, expander._animation.get('node'));
        },

        test_loaded_is_true_if_no_loader_is_defined: function() {
            var icon = Y.Node.create('<p></p>'),
                content = Y.Node.create('<p></p>');
            var expander = new module.Expander(icon, content);
            Y.Assert.isTrue(expander.loaded);
        },

        test_loaded_is_false_if_loader_is_defined: function() {
            var icon = Y.Node.create('<p></p>'),
                content = Y.Node.create('<p></p>');
            var config = {loader: function() {}};
            var expander = new module.Expander(icon, content, config);
            Y.Assert.isFalse(expander.loaded);
        },

        test_setUp_preserves_icon_content: function() {
            var root = this.makeExpanderHooks();
            root.one('.icon').set('text', "Click here");
            var icon = this.makeExpander(root).icon_node;
            Y.Assert.areEqual("Click here", icon.get('text'));
        },

        test_setUp_creates_collapsed_icon_by_default: function() {
            var icon = this.makeExpander().icon_node;
            Y.Assert.isTrue(icon.hasClass('sprite'));
            Y.Assert.isFalse(icon.hasClass('treeExpanded'));
            Y.Assert.isTrue(icon.hasClass('treeCollapsed'));
        },

        test_setUp_reveals_icon: function() {
            var root = this.makeExpanderHooks();
            var icon = root.one('.icon');
            icon.addClass('unseen');
            var expander = this.makeExpander(root);
            Y.Assert.isFalse(icon.hasClass('unseen'));
        },

        test_setUp_hides_content_by_default: function() {
            var content = this.makeExpander().content_node;
            Y.Assert.isTrue(content.hasClass('unseen'));
        },

        test_setUp_creates_expanded_icon_if_content_is_expanded: function() {
            var root = this.makeExpanderHooks({expanded: true});
            var icon = this.makeExpander(root).icon_node;
            Y.Assert.isTrue(icon.hasClass('treeExpanded'));
            Y.Assert.isFalse(icon.hasClass('treeCollapsed'));
        },

        test_setUp_reveals_content_if_content_is_expanded: function() {
            var root = this.makeExpanderHooks({expanded: true});
            var content = this.makeExpander(root).content_node;
            Y.Assert.isFalse(content.hasClass('unseen'));
        },

        test_setUp_does_not_run_loader_by_default: function() {
            var loader_has_run = false;
            var loader = function() {
                loader_has_run = true;
            };
            this.makeExpander(
                this.makeExpanderHooks(), {config: {loader: loader}});
            Y.Assert.isFalse(loader_has_run);
        },

        test_setUp_runs_loader_if_content_is_expanded: function() {
            var loader_has_run = false;
            var loader = function() {
                loader_has_run = true;
            };
            this.makeExpander(
                this.makeExpanderHooks({expanded: true}),
                {config: {loader: loader}});
            Y.Assert.isTrue(loader_has_run);
        },

        test_setUp_installs_click_handler: function() {
            var expander = this.makeExpander();
            var render_has_run = false;
            var fake_render = function() {
                render_has_run = true;
            };
            expander.render = fake_render;
            expander.icon_node.simulate('click');
            Y.Assert.isTrue(render_has_run);
        },

        test_setUp_calls_foldContentNode_no_anim: function() {
            var foldContentNode_animate_arg = false;
            var fake_foldContentNode = function(expanded, no_animate) {
                foldContentNode_animate_arg = no_animate;
            };
            var old_method = module.Expander.prototype.foldContentNode;
            module.Expander.prototype.foldContentNode = fake_foldContentNode;
            var expander = this.makeExpander();
            expander.foldContentNode = fake_foldContentNode;
            Y.Assert.isTrue(foldContentNode_animate_arg);
            module.Expander.prototype.foldContentNode = old_method;
        },

        test_createByCSS_creates_expander: function() {
            var root = this.makeExpanderHooks();
            this.findTestHookTag().appendChild(root);
            module.createByCSS('.hook', '.icon', '.content');
            Y.Assert.isTrue(root.one('.content').hasClass('unseen'));
        },

        test_toggle_retains_content: function() {
            var root = this.makeExpanderHooks();
            root.one('.content').set('text', "Contents here");
            var expander = this.makeExpander(root);
            root.one('.icon').simulate('click');
            root.one('.icon').simulate('click');
            Y.Assert.areEqual(
                "Contents here", expander.content_node.get('text'));
        },

        test_loader_runs_only_once: function() {
            var loader_runs = 0;
            var loader = function() {
                loader_runs++;
            };
            var expander = this.makeExpander(
                this.makeExpanderHooks(), {config: {loader: loader}});
            expander.icon_node.simulate('click');
            expander.icon_node.simulate('click');
            expander.icon_node.simulate('click');
            Y.Assert.areEqual(1, loader_runs);
        },

        test_receive_replaces_contents: function() {
            var expander = this.makeExpander();
            var ajax_result = this.makeNode("ajax-result");
            expander.receive(ajax_result);
            Y.Assert.isTrue(expander.content_node.hasChildNodes());
            var children = expander.content_node.get('children');
            Y.Assert.areEqual(1, children.size());
            Y.Assert.areEqual(ajax_result, children.item(0));
        },

        test_receive_success_leaves_loaded: function() {
            var expander = this.makeExpander();
            Y.Assert.isTrue(expander.loaded);
            expander.receive('');
            Y.Assert.isTrue(expander.loaded);
        },

        test_receive_failure_resets_loaded: function() {
            var expander = this.makeExpander();
            Y.Assert.isTrue(expander.loaded);
            expander.receive('', true);
            Y.Assert.isFalse(expander.loaded);
        },

        test_receive_stops_and_restarts_animation: function() {
            var expander = this.makeExpander();
            var anim = new FakeAnim();
            anim.set('running', true);
            expander._animation = anim;
            expander.receive('');
            // Animation is first stopped, then restarted with run().
            Y.ArrayAssert.itemsAreSame(
                ['stop', 'run'], anim.call_stack);
        },

        test_receive_restarts_at_current_height: function() {
            var expander = this.makeExpander();

            var anim = new FakeAnim();
            expander._animation = anim;

            // We've got a half (well, 40%) open container node
            // with current height at 2px.
            var content_node = Y.Node.create('<div />')
                .setStyle('height', '2px');
            this.findTestHookTag().appendChild(content_node);
            expander.content_node = expander._animate_node = content_node;

            // Full desired content height of 5px.
            var content = Y.Node.create('<div />')
                .setStyle('height', '5px');

            expander.receive(content);
            // We get an integer from scrollHeight, and pixels from height.
            Y.Assert.areEqual(5, anim.get('to').height);
            Y.Assert.areEqual('2px', anim.get('from').height);
        },

        test_foldContentNode_expand_no_animation: function() {
            var expander = this.makeExpander();

            var anim = new FakeAnim();
            expander._animation = anim;

            // First parameter is true for expand, false for folding.
            // Second parameter indicates if no animation should be used
            // (true for no animation, anything else otherwise).
            expander.foldContentNode(true, true);

            // No anim.run() calls have been executed.
            Y.ArrayAssert.itemsAreEqual([], anim.call_stack);
            // And unseen CSS class has been removed.
            Y.Assert.isFalse(
                expander.content_node.hasClass("unseen"));
        },

        test_foldContentNode_fold_no_animation: function() {
            var expander = this.makeExpander();

            var anim = new FakeAnim();
            expander._animation = anim;

            // First parameter is true for expand, false for folding.
            // Second parameter indicates if no animation should be used
            // (true for no animation, anything else otherwise).
            expander.foldContentNode(false, true);

            // No anim.run() calls have been executed.
            Y.ArrayAssert.itemsAreEqual([], anim.call_stack);
            // And unseen CSS class has been added.
            Y.Assert.isTrue(
                expander.content_node.hasClass("unseen"));
        },

        test_foldContentNode_expand: function() {
            // Expanding a content node sets the animation direction
            // as appropriate ('reverse' to false) and removes the
            // 'unseen' CSS class.
            var expander = this.makeExpander();

            var anim = new FakeAnim();
            anim.set('reverse', true);
            expander._animation = anim;

            expander.foldContentNode(true);

            // Reverse flag has been toggled.
            Y.Assert.isFalse(anim.get('reverse'));
            // 'unseen' CSS class has been removed.
            Y.Assert.isFalse(expander.content_node.hasClass("unseen"));
            // Animation is shown.
            Y.ArrayAssert.itemsAreEqual(['run'], anim.call_stack);
        },

        test_foldContentNode_fold: function() {
            // Folding a content node sets the animation direction
            // as appropriate ('reverse' to false) and removes the
            // 'unseen' CSS class.
            var expander = this.makeExpander();

            var anim = new FakeAnim();
            anim.set('reverse', true);
            expander._animation = anim;
            // Initially expanded (with no animation).
            expander.foldContentNode(true, true);

            // Now fold it back.
            expander.foldContentNode(false);

            // Reverse flag has been toggled.
            Y.Assert.isTrue(anim.get('reverse'));
            // Animation is shown.
            Y.ArrayAssert.itemsAreEqual(['run'], anim.call_stack);
            // 'unseen' CSS class is added back, but only when
            // the animation completes.
            Y.Assert.isFalse(expander.content_node.hasClass("unseen"));
            anim.fire('end');
            Y.Assert.isTrue(expander.content_node.hasClass("unseen"));
        },

        test_foldContentNode_fold_expand: function() {
            // Quickly folding then re-expanding a node doesn't
            // set the 'unseen' flag.
            var expander = this.makeExpander();
            var anim = new FakeAnim();
            anim.set('reverse', true);
            expander._animation = anim;
            // Initially expanded (with no animation).
            expander.foldContentNode(true, true);

            // Now fold it.
            expander.foldContentNode(false);
            Y.Assert.isFalse(expander.content_node.hasClass("unseen"));
            // And expand it before animation was completed.
            expander.foldContentNode(true);
            // When animation for folding completes, it does not
            // set the 'unseen' CSS class because expanding is now
            // in progress instead.
            anim.fire('end');
            Y.Assert.isFalse(expander.content_node.hasClass("unseen"));
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

