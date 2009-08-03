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
        LP.client.Launchpad.prototype.named_post = function(url, func, config) {
            config.on.success();
        };
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

    test_can_be_instantiated: function() {
        Assert.isInstanceOf(
            Y.ChoiceSource, this.choice_edit, "ChoiceSource not instantiated.");
    },

    test_choicesource_leaves_value_in_page: function() {
        var st = Y.get(document).query("#affectsmetoo");
        // value in page should be left alone if config.value does not
        // correspond to any item in config.items.
        Assert.isEqual(
            "Does this bug affect you?", st.query(".value").get("innerHTML"),
            "ChoiceSource is not overriding displayed value in HTML");
    },

    test_clicking_creates_choicelist: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        Assert.isNotNull(this.choice_edit._choice_list,
          "ChoiceList object is not created");
        Assert.isNotNull(Y.get(document).query(".yui-ichoicelist"),
          "ChoiceList HTML is not being added to the page");
    },

    test_right_clicking_doesnt_create_choicelist: function() {
        simulate(this.choice_edit.get('boundingBox'),
                 '.value', 'mousedown', { button: 2 });
        Assert.isNull(Y.get(document).query(".yui-ichoicelist"),
          "ChoiceList created when the right mouse button was clicked");
    },

    test_choicelist_has_correct_values: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        var self = this;
        Y.each(this.config.items, function(configitem) {
            var found = false;
            Y.each(self.choice_edit._choice_list.get("items"), function(choiceitem) {
                if (choiceitem.name == configitem.name) {
                    found = true;
                }
            });
            Assert.isTrue(found,
              "Item " + configitem.name + " is passed to ChoiceSource but is " +
              "not in ChoiceList.items");
        });
        var choicelistcount = this.choice_edit._choice_list.get("items").length;
        var configcount = this.config.items.length;
        Assert.isEqual(choicelistcount, configcount,
          "ChoiceList HTML list is a different length (" + choicelistcount +
          ") than config items list (" + configcount + ")");
    },

    test_choicelist_html_has_correct_values: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        var configcount = this.config.items.length;
        var choicelist_lis = Y.get(document).queryAll(".yui-ichoicelist li");
        Assert.isEqual(choicelist_lis.size(), configcount,
          "ChoiceList HTML list is a different length (" + choicelist_lis.size() +
          ") than config items list (" + configcount + ")");
        // confirm self each LI matches with an item
        var self = this;
        choicelist_lis.each(function(li) {
            var text = li.get("text");
            var found = false;
            for (var i=0; i<self.config.items.length; i++) {
                if (self.config.items[i].name == text) {
                    found = true;
                    break;
                }
            }
            Assert.isTrue(found, "Page LI '" + text +
               "' did not come from a config item");
        });
    },

    test_choicelist_html_has_current: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        var configcount = this.config.items.length;
        var choicelist_lis = Y.get(document).queryAll(".yui-ichoicelist li");

        var self = this;
        var asserted;
        var test_li = function(li) {
            var text = li.get("text");
            for (var i=0; i<self.config.items.length; i++) {
                if (self.config.items[i].name == text) {
                    if (self.config.items[i].value == self.config.value) {
                        Assert.isEqual(li.query("span.current").size(), 1,
                          "Page LI '" + text + "' was not marked as current");
                        asserted = true;
                    }
                    break;
                }
            }
        };

        // When config.value does not correspond to any item in
        // config.items, no LI in the choice list will be marked with
        // the "current" style.
        asserted = false;
        choicelist_lis.each(test_li);
        Assert.isFalse(asserted, "There was a current LI item");

        // When a choice is made, the current value is marked with the
        // "current" class in the choice list.
        this.choice_edit.after('valueChange', function() { self.resume(); });
        simulate(this.choice_edit._choice_list.get('boundingBox'),
                'li a[href$=true]', 'click');
        this.wait(3000, function() {
            simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
            asserted = false;
            choicelist_lis.each(test_li);
            Assert.isTrue(asserted, "There was no current LI item");
        });
    },

    test_clicking_choicelist_item_fires_signal: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        var self = this;
        this.choice_edit._choice_list.on("valueChosen", function() {
            self.resume();
        });
        // simulate a click on the "fix released" option, which is
        // (a) enabled
        // (b) not the current option
        simulate(this.choice_edit._choice_list.get('boundingBox'),
          'li a[href$=true]', 'click');
        this.wait(3000, function() { Assert.isTrue(false,
          "valueChosen signal was not fired"); });
    },

    test_clicking_choicelist_item_does_green_flash: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        var self = this;
        Y.lazr.anim.green_flash = function() {
          return {
              run: function() {
                  self.resume();
              }
          };
        };
        simulate(this.choice_edit._choice_list.get('boundingBox'),
          'li a[href$=true]', 'click');
        this.wait(3000, function() {
            Assert.isTrue(false, "green_flash animation was not fired");
        });
    },

    test_clicking_choicelist_item_sets_page_value: function() {
        var st = Y.get(document).query("#affectsmetoo");
        // The page value is set to item.name of the selected item.
        simulate(this.choice_edit.get('boundingBox'), '.value', 'mousedown');
        simulate(this.choice_edit._choice_list.get('boundingBox'),
          'li a[href$=true]', 'click');
        Assert.isEqual(
            "This bug affects me too",
            st.query(".value").get("innerHTML"),
            "Chosen choicelist item is not displayed in HTML (value is '" +
                st.query(".value").get("innerHTML") + "')");
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
