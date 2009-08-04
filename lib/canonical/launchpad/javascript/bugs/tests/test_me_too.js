/* Copyright (c) 2008, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../icing/yui/current/build/',
    filter: 'raw',
    combine: false
    }).use('event', 'bugs.bugtask_index', 'node', 'yuitest', 'widget-stack', 'console',
        function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;

Assert.isEqual = function(a, b, msg) {
    Assert.isTrue(a == b, msg);
};

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var rawnode = Y.Node.getDOMNode(widget.query(selector));
    Y.Event.simulate(rawnode, evtype, options);
}

/* Helper function to clean up a dynamically added widget instance. */
function cleanup_widget(widget) {
    // Nuke the boundingBox, but only if we've touched the DOM.
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        if (bb.get('parentNode')) {
            bb.get('parentNode').removeChild(bb);
        }
    }
    // Kill the widget itself.
    widget.destroy();
}

var suite = new Y.Test.Suite("Bugtask Me-Too Choice Edit Tests");

suite.add(new Y.Test.Case({

    name: 'me_too_choice_edit_basics',

    setUp: function() {
        // Monkeypatch LP.client to avoid network traffic and to make
        // some things work as expected.
        LP.client.Launchpad.prototype.named_post = (
            function(url, func, config) {
                config.on.success();
            }
        );
        LP.client.cache.bug = {
            self_link: "http://bugs.example.com/bugs/1234"
        };
        // add the in-page HTML
        var inpage = Y.Node.create([
            '<span id="affectsmetoo">',
            '  <span class="static">',
            '    <img src="https://bugs.edge.launchpad.net/@@/flame-icon" alt="" />',
            '    This bug affects me too',
            '    <a href="+affectsmetoo">',
            '      <img class="editicon" alt="Edit"',
            '           src="https://bugs.edge.launchpad.net/@@/edit" />',
            '    </a>',
            '  </span>',
            '  <span class="dynamic unseen">',
            '    <img class="editicon" alt="Edit"',
            '         src="https://bugs.edge.launchpad.net/@@/edit" />',
            '    <a href="+affectsmetoo" class="js-action"',
            '       ><span class="value">Does this bug affect you?</span></a>',
            '    <img src="https://bugs.edge.launchpad.net/@@/flame-icon" alt=""/>',
            '  </span>',
            '</span>'].join(''));
        Y.get("body").appendChild(inpage);
        var me_too_content = Y.get('#affectsmetoo');
        this.config = {
            contentBox: me_too_content,
            value: null,
            title: 'This bug:',
            items: [
                {name: 'Affects me too', value: true,
                 source_name: 'This bug affects me too',
                 disabled: false},
                {name: 'Does not affect me', value: false,
                 source_name: "This bug doesn't affect me",
                 disabled: false}
            ],
            elementToFlash: me_too_content,
            backgroundColor: '#FFFFFF'
        };
        this.choice_edit = new Y.bugs._MeTooChoiceSource(this.config);
        this.choice_edit.render();
    },

    tearDown: function() {
        if (this.choice_edit._choice_list) {
            cleanup_widget(this.choice_edit._choice_list);
        }
        var status = Y.get("document").query("#affectsmetoo");
        if (status) {
            status.get("parentNode").removeChild(status);
        }
    },

    /**
     * The choice edit should be displayed inline.
     */
    test_is_inline: function() {
        var display = this.choice_edit.get('boundingBox').getStyle('display');
        Assert.isEqual(
            display, 'inline', "Not displayed inline, display is: " + display);
    },

    /**
     * The .static area should be hidden by adding the "unseen" class.
     */
    test_hide_static: function() {
        var static_area = this.choice_edit.get('contentBox').query('.static');
        Assert.isTrue(
            static_area.hasClass('unseen'), "Static area is not hidden.");
    },

    /**
     * The .dynamic area should be shown by removing the "unseen" class.
     */
    test_hide_dynamic: function() {
        var dynamic_area = this.choice_edit.get('contentBox').query('.dynamic');
        Assert.isFalse(
            dynamic_area.hasClass('unseen'), "Dynamic area is hidden.");
    },

    /**
     * The flame icon should be hidden initially.
     */
    test_flame_hidden_initially: function() {
        var flame_icon = this.choice_edit.get('flame_icon');
        Assert.isTrue(flame_icon.hasClass('unseen'), "Flame is not hidden.");
    },

    /**
     * The flame icon should be hidden when the user has made a
     * negative choice (i.e. "Does not affect me").
     */
    test_flame_hidden_with_negative_choice: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        simulate(this.choice_edit._choice_list.get('boundingBox'),
                 'li a[href$=false]', 'click');
        var flame_icon = this.choice_edit.get('flame_icon');
        Assert.isTrue(flame_icon.hasClass('unseen'), "Flame is not hidden.");
    },

    /**
     * The flame icon should be shown when the user has made a
     * positive choice (i.e. "Affects me too").
     */
    test_flame_hidden_with_positive_choice: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        simulate(this.choice_edit._choice_list.get('boundingBox'),
                 'li a[href$=true]', 'click');
        var flame_icon = this.choice_edit.get('flame_icon');
        Assert.isFalse(flame_icon.hasClass('unseen'), "Flame is hidden.");
    },

    /**
     * The UI should be in a waiting state while the save process is
     * executing and return to a non-waiting state once it has
     * finished.
     */
    test_ui_waiting_for_success: function() {
        this.do_test_ui_waiting('success');
    },

    /**
     * The UI should be in a waiting state while the save process is
     * executing and return to a non-waiting state even if the process
     * fails.
     */
    test_ui_waiting_for_failure: function() {
        this.do_test_ui_waiting('failure');
    },

    /**
     * Helper function that does the leg work for the
     * test_ui_waiting_* methods.
     */
    do_test_ui_waiting: function(callback) {
        var edit_icon = this.choice_edit.get('editicon');
        // The spinner should not be displayed at first.
        Assert.isNull(
            edit_icon.get('src').match(/\/spinner$/),
            "The edit icon is displaying a spinner at rest.");
        // The spinner should not be displayed after opening the
        // choice list.
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        Assert.isNull(
            edit_icon.get('src').match(/\/spinner$/),
            "The edit icon is displaying a spinner after opening the choice list.");
        // The spinner should be visible during the interval between a
        // choice being made and a response coming back from Launchpad
        // that the choice has been saved.
        var edit_icon_src_during_save;
        // Patch the named_post method to simulate success or failure,
        // as determined by the callback argument. We cannot make
        // assertions in this method because exceptions are swallowed
        // somewhere. Instead, we save something testable to a local
        // var.
        LP.client.Launchpad.prototype.named_post = (
            function(url, func, config) {
                edit_icon_src_during_save = edit_icon.get('src');
                config.on[callback]();
            }
        );
        simulate(this.choice_edit._choice_list.get('boundingBox'),
                 'li a[href$=true]', 'click');
        Assert.isNotNull(
            edit_icon_src_during_save.match(/\/spinner$/),
            "The edit icon is not displaying a spinner during save.");
        // The spinner should not be displayed once a choice has been
        // saved.
        Assert.isNull(
            edit_icon.get('src').match(/\/spinner$/),
            "The edit icon is displaying a spinner once the choice has been made.");
    },

    /**
     * Test that the save call back to Launchpad makes sense.
     */
    test_save_data: function() {
        var url, func, config;
        LP.client.Launchpad.prototype.named_post = (
            function(f_url, f_func, f_config) {
                url = f_url, func = f_func, config = f_config;
                config.on.success();
            }
        );
        // Simulate selecting something.
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        simulate(this.choice_edit._choice_list.get('boundingBox'),
                 'li a[href$=true]', 'click');
        // See what we've got.
        Assert.isEqual(url, "http://bugs.example.com/bugs/1234",
                       "LP client call to wrong URL.");
        Assert.isEqual(func, "markUserAffected",
                       "LP client call to wrong method.");
        Assert.isNotNull(config.on);
        Assert.isNotNull(config.on.success);
        Assert.isNotNull(config.on.failure);
        Assert.isNotNull(config.parameters);
        Assert.isTrue(config.parameters.affected);
    }

}));

Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
