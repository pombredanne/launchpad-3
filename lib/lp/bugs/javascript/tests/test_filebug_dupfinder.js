YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.filebug_dupefinder',
        'node-event-simulate', function(Y) {

var suite = new Y.Test.Suite("lp.bugs.filebug_dupefinder Tests");
var module = Y.lp.bugs.filebug_dupefinder;

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var node_to_use = widget;
    if (selector !== undefined) {
        node_to_use = widget.one(selector);
    }
    var rawnode = Y.Node.getDOMNode(node_to_use);
    Y.Event.simulate(rawnode, evtype, options);
}

function IOStub(caller){
    if (!(this instanceof IOStub)) {
        throw new Error("Constructor called as a function");
    }
    this.io = function(url, config) {
        var response = {responseText: ''};
        // We may have been passed text to use in the response.
        if (Y.Lang.isValue(arguments.callee.responseText)) {
            response.responseText = arguments.callee.responseText;
        }
        // We currently only support calling the success handler.
        config.on.success(undefined, response, arguments.callee.args);
        // After calling the handler, resume the test.
        if (Y.Lang.isFunction(arguments.callee.doAfter)) {
            caller.resume(arguments.callee.doAfter);
        }
    };
}

suite.add(new Y.Test.Case({
    name: 'Test filebug form manipulation.',

    setUp: function() {
        var test_html = Y.Node.create([
            '<div id="filebug-test">',
            '    <div id="spinner"></div>',
            '    <div id="possible-duplicates">',
            '    </div>',
            '    <div style="opacity: 0; display: none" class="transparent" id="filebug-form-container">',
            '        <div id="bug_reporting_form">',
            '            <label for="field.title">Summary:</label>',
            '            <input type="text" value="" size="40" name="field.title" id="field.title"/>',
            '            <div>',
            '                <form id="filebug-form" method="post" action="#">',
            '                    <label for="field.comment">Comment:</label>',
            '                    <input type="text" value="" size="40" name="field.comment" id="field.comment"/>',
            '                    <div class="actions">',
            '                        <input type="submit" class="button" value="Submit Bug Report" name="field.actions.submit_bug" id="field.actions.submit_bug"/>',
            '                    </div>',
            '                </form>',
            '            </div>',
            '        </div>',
            '    </div>',
            '    <a id="filebug-base-url" href="https://bugs.launchpad.dev/"></a>',
            '    <a id="filebug-form-url" href="https://bugs.launchpad.dev/firefox/+filebug-inline-form"></a>',
            '    <a id="duplicate-search-url" href="https://bugs.launchpad.dev/firefox/+filebug-show-similar"></a>',
            '</div>'].join(''));
        Y.one("#test-content").appendChild(test_html);
        this.config = {};
        this.config.yio = new IOStub(this);
        module.setup_config(this.config);
    },

    tearDown: function() {
        var filebug = Y.one("#filebug-test");
        if (filebug) {
            filebug.get("parentNode").removeChild(filebug);
        }
    },

    /**
     * Some helper functions
     */
    selectNode: function(node, selector) {
        if (!Y.Lang.isValue(node)) {
            node = Y.one('#test-root');
        }
        var node_to_use = node;
        if (Y.Lang.isValue(selector)) {
            node_to_use = node.one(selector);
        }
        return node_to_use;
    },

    assertStyleValue: function(node, selector, style, value) {
        node = this.selectNode(node, selector);
        Y.Assert.areEqual(value, node.getStyle(style));
    },

    assertIsVisible: function(node, selector) {
        this.assertStyleValue(node, selector, 'display', 'block');
    },

    assertIsNotVisible: function(node, selector) {
        this.assertStyleValue(node, selector, 'display', 'none');
    },

    assertNodeText: function(node, selector, text) {
        node = this.selectNode(node, selector);
        Y.Assert.areEqual(text, node.get('innerHTML'));
    },


    /**
     * A user first searches for duplicate bugs. If there are no duplicates
     * the file bug form should be visible for bug details to be entered.
     */
    test_no_dups_search_shows_filebug_form: function() {
        // filebug container should not initially be visible
        this.assertIsNotVisible(null, '#filebug-form-container');
        var search_text = Y.one(Y.DOM.byId('field.search'));
        search_text.set('value', 'foo');
        var search_button = Y.one(Y.DOM.byId('field.actions.search'));
        // The search button should initially say 'Next'
        Y.Assert.areEqual('Next', search_button.get('value'));
        this.config.yio.io.responseText = 'No similar bug reports.';
        this.config.yio.io.doAfter = function() {
            // filebug container should be visible after the dup search
            this.assertIsVisible(null, '#filebug-form-container');
            var dups_node = Y.one("#possible-duplicates");
            this.assertNodeText(
                    dups_node, undefined, 'No similar bug reports.');
        };
        simulate(search_button, undefined, 'click');
        this.wait();
    },

    /**
     * A user first searches for duplicate bugs. If there are duplicates
     * the dups should be listed and the file bug form should not be visible.
     */
    test_dups_search_shows_dup_info: function() {
        // filebug container should not initially be visible
        this.assertIsNotVisible(null, '#filebug-form-container');
        var search_text = Y.one(Y.DOM.byId('field.search'));
        search_text.set('value', 'foo');
        var search_button = Y.one(Y.DOM.byId('field.actions.search'));
        this.config.yio.io.responseText = ([
                '<img id="bug-details-expander" ',
                'class="bug-already-reported-expander" ',
                'src="/@@/treeCollapsed">',
                '<input type="button" value="No, I need to report a new bug"',
                ' name="field.bug_already_reported_as"',
                ' id="bug-not-already-reported" style="display: block">'
                ].join(''));
        this.config.yio.io.doAfter = function() {
            // filebug container should not be visible when there are dups
            this.assertIsNotVisible(null, '#filebug-form-container');
            // we should have a 'new bug' button
            this.assertIsVisible(null, '#bug-not-already-reported');
            // The search button should say 'Check again'
            Y.Assert.areEqual('Check again', search_button.get('value'));
        };
        simulate(search_button, undefined, 'click');
        this.wait();
    },

    /**
     * A user first searches for duplicate bugs. They can start typing in some
     * detail. They can search again for dups and their input should be
     * retained.
     */
    test_dups_search_retains_user_input_when_no_dups: function() {
        // filebug container should not initially be visible
        this.assertIsNotVisible(null, '#filebug-form-container');
        var search_text = Y.one(Y.DOM.byId('field.search'));
        search_text.set('value', 'foo');
        var search_button = Y.one(Y.DOM.byId('field.actions.search'));
        this.config.yio.io.responseText = 'No similar bug reports.';
        this.config.yio.io.doAfter = function() {
            var comment_text = Y.one(Y.DOM.byId('field.comment'));
            comment_text.set('value', 'an error occurred');
            this.config.yio.io.doAfter = function() {
                // The user input should be retained
                Y.Assert.areEqual(
                    'an error occurred', comment_text.get('value'));
            };
            simulate(search_button, undefined, 'click');
            this.wait();
        };
        simulate(search_button, undefined, 'click');
        this.wait();
    },

    /**
     * A user first searches for duplicate bugs and there are none.
     * They can start typing in some detail. They can search again for dups
     * and their input should be retained even when there are dups and they
     * have to click the "No, this is a new bug" button.
     */
    test_dups_search_retains_user_input_when_dups: function() {
        // filebug container should not initially be visible
        this.assertIsNotVisible(null, '#filebug-form-container');
        var search_text = Y.one(Y.DOM.byId('field.search'));
        search_text.set('value', 'foo');
        var search_button = Y.one(Y.DOM.byId('field.actions.search'));
        this.config.yio.io.responseText = 'No similar bug reports.';
        this.config.yio.io.doAfter = function() {
            var comment_text = Y.one(Y.DOM.byId('field.comment'));
            comment_text.set('value', 'an error occurred');
            this.config.yio.io.responseText = ([
                    '<img id="bug-details-expander" ',
                    'class="bug-already-reported-expander" ',
                    'src="/@@/treeCollapsed">',
                    '<input type="button" value="No, I need to report a bug"',
                    ' name="field.bug_already_reported_as"',
                    ' id="bug-not-already-reported" style="display: block">'
                    ].join(''));
            this.config.yio.io.doAfter = function() {
                var new_bug_button = Y.one('#bug-not-already-reported');
                simulate(new_bug_button, undefined, 'click');
                // filebug container should be visible
                this.assertIsVisible(null, '#filebug-form-container');
                // The user input should be retained
                Y.Assert.areEqual(
                    'an error occurred', comment_text.get('value'));
            };
            simulate(search_button, undefined, 'click');
            this.wait();
        };
        simulate(search_button, undefined, 'click');
        this.wait();
    }

}));

var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

// Configure the javascript module under test. In production, the
// setup_dupe_finder() is called from the page template. We need to pass in
// a stub io handler here so that the XHR call made during set up is ignored.
var config = {};
config.yio = new IOStub();
module.setup_config(config);
module.setup_dupe_finder();

Y.on('domready', function(e) {
    Y.Test.Runner.run();
});
});
