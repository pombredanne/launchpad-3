/* Copyright (c) 2008, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lazr.choiceedit',
           'event', 'event-simulate', 'widget-stack', function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var rawnode = Y.Node.getDOMNode(widget.one(selector));
    Y.Event.simulate(rawnode, evtype, options);
}

/* Helper function to clean up a dynamically added widget instance. */
function cleanup_widget(widget) {
    // Nuke the boundingBox, but only if we've touched the DOM.
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        if (Y.Node.getDOMNode(bb)) {
            if (bb.get('parentNode')) {
                bb.get('parentNode').removeChild(bb);
            }
        }
    }
    // Kill the widget itself.
    widget.destroy();
}

var suite = new Y.Test.Suite("LAZR Choice Edit Tests");

function setUp() {
    // add the in-page HTML
    var inpage = Y.Node.create([
        '<p id="thestatus">',
        'Status: <span class="value">Unset</span> ',
        '<img class="editicon" src="https://bugs.edge.launchpad.net/@@/edit">',
        '</p>'].join(''));
    Y.one("body").appendChild(inpage);
    this.config = this.make_config();
    this.choice_edit = new Y.ChoiceSource(this.config);
    this.choice_edit.render();
}

function tearDown() {
    if (this.choice_edit._choice_list) {
        cleanup_widget(this.choice_edit._choice_list);
    }
    var status = Y.one("document").one("#thestatus");
    if (status) {
        status.get("parentNode").removeChild(status);
    }
}

suite.add(new Y.Test.Case({

    name: 'choice_edit_basics',

    setUp: setUp,

    tearDown: tearDown,

    make_config: function() {
        return {
            contentBox:  '#thestatus',
            value:       'incomplete',
            title:       'Change status to',
            items: [
              { name: 'New', value: 'new', style: '',
                help: '', disabled: false },
              { name: 'Invalid', value: 'invalid', style: '',
                help: '', disabled: true },
              { name: 'Incomplete', value: 'incomplete', style: '',
                help: '', disabled: false },
              { name: 'Fix Released', value: 'fixreleased', style: '',
                help: '', disabled: false },
              { name: 'Fix Committed', value: 'fixcommitted', style: '',
                help: '', disabled: true },
              { name: 'In Progress', value: 'inprogress', style: '',
                help: '', disabled: false },
              { name: 'Stalled', value: 'stalled', style: '',
                help: '', disabled: false, source_name: 'STALLED' }
            ]
        };
    },

    test_can_be_instantiated: function() {
        Assert.isInstanceOf(
            Y.ChoiceSource, this.choice_edit, "ChoiceSource not instantiated.");
    },

    test_choicesource_overrides_value_in_page: function() {
        var st = Y.one(document).one("#thestatus");
        // value in page should be set to the config.items.name corresponding to
        // config.value
        Assert.areEqual("Incomplete", st.one(".value").get("innerHTML"),
                        "ChoiceSource is not overriding displayed value in HTML");
    },

    test_clicking_creates_choicelist: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        Assert.isNotNull(this.choice_edit._choice_list,
          "ChoiceList object is not created");
        Assert.isNotNull(Y.one(document).one(".yui3-ichoicelist"),
          "ChoiceList HTML is not being added to the page");
    },

    test_right_clicking_doesnt_create_choicelist: function() {
        simulate(this.choice_edit.get('boundingBox'),
                 '.value', 'click', { button: 2 });
        Assert.isNull(Y.one(document).one(".yui3-ichoicelist"),
          "ChoiceList created when the right mouse button was clicked");
    },

    test_choicelist_has_correct_values: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        var that = this;
        Y.each(this.config.items, function(configitem) {
            var found = false;
            Y.each(that.choice_edit._choice_list.get("items"), function(choiceitem) {
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
        Assert.areEqual(choicelistcount, configcount,
          "ChoiceList HTML list is a different length (" + choicelistcount +
          ") than config items list (" + configcount + ")");
    },

    test_choicelist_html_has_correct_values: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        var configcount = this.config.items.length;
        var choicelist_lis = Y.one(document).all(".yui3-ichoicelist li");
        Assert.areEqual(choicelist_lis.size(), configcount,
          "ChoiceList HTML list is a different length (" + choicelist_lis.size() +
          ") than config items list (" + configcount + ")");
        // confirm that each LI matches with an item
        var that = this;
        choicelist_lis.each(function(li) {
            var text = li.get("text");
            var found = false;
            for (var i=0; i<that.config.items.length; i++) {
                if (that.config.items[i].name == text) {
                    found = true;
                    break;
                }
            }
            Assert.isTrue(found, "Page LI '" + text +
               "' did not come from a config item");
        });
    },

    test_choicelist_html_has_disabled: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        var configcount = this.config.items.length;
        var choicelist_lis = Y.one(document).all(".yui3-ichoicelist li");
        // confirm that disabled LIs are disabled
        var that = this;
        choicelist_lis.each(function(li) {
            var text = li.get("text");
            for (var i=0; i<that.config.items.length; i++) {
                if (that.config.items[i].name == text) {
                    if (that.config.items[i].disabled) {
                        Assert.isNotNull(li.one("span.disabled"),
                          "Page LI '" + text + "' was not disabled");
                    }
                    break;
                }
            }
        });
    },

    test_choicelist_html_has_current: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        var configcount = this.config.items.length;
        var choicelist_lis = Y.one(document).all(".yui3-ichoicelist li");
        // confirm that current value has an LI with current style
        var that = this;
        var asserted = false;
        choicelist_lis.each(function(li) {
            var text = li.get("text");
            for (var i=0; i<that.config.items.length; i++) {
                if (that.config.items[i].name == text) {
                    if (that.config.items[i].value == that.config.value) {
                        Assert.isNotNull(li.one("span.current"),
                          "Page LI '" + text + "' was not marked as current");
                        asserted = true;
                    }
                    break;
                }
            }
        });
        Assert.isTrue(asserted, "There was no current LI item");
    },

    test_clicking_choicelist_item_fires_signal: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        var that = this;
        var fired = false;
        this.choice_edit._choice_list.on("valueChosen", function() {
            fired = true;
        });
        // simulate a click on the "fix released" option, which is
        // (a) enabled
        // (b) not the current option
        simulate(this.choice_edit._choice_list.get('boundingBox'),
            'li a[href$=fixreleased]', 'click');
        Assert.isTrue(fired, "valueChosen signal was not fired");
    },

    test_clicking_choicelist_item_does_green_flash: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        var that = this;
        var green_flash = Y.lp.anim.green_flash;
        var flashed = false;
        Y.lp.anim.green_flash = function() {
          return {
              run: function() {
                  flashed = true;
              }
          };
        };
        simulate(this.choice_edit._choice_list.get('boundingBox'),
            'li a[href$=fixreleased]', 'click');
        Assert.isTrue(flashed, "green_flash animation was not fired");
        Y.lp.anim.green_flash = green_flash;
    },

    test_clicking_choicelist_item_sets_page_value: function() {
        var st = Y.one(document).one("#thestatus");
        // The page value is set to item.name of the selected item.
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        simulate(this.choice_edit._choice_list.get('boundingBox'),
          'li a[href$=fixreleased]', 'click');
        Assert.areEqual("Fix Released", st.one(".value").get("innerHTML"),
           "Chosen choicelist item is not displayed in HTML (value is '" +
           st.one(".value").get("innerHTML") + "')");
    },

    test_clicking_choicelist_item_sets_page_source_name: function() {
        var st = Y.one(document).one("#thestatus");
        // By default, the page value is set to item.name of the
        // selected item, but this can be overridden by specifying
        // item.source_name.
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        var choice_list_bb = this.choice_edit._choice_list.get('boundingBox');
        var stalled_in_list = choice_list_bb.one('li a[href$=stalled]');
        Assert.areEqual(
            "Stalled", stalled_in_list.get('innerHTML'),
            "ChoiceList item not displayed correctly: " +
                stalled_in_list.get('innerHTML'));
        simulate(choice_list_bb, 'li a[href$=stalled]', 'click');
        Assert.areEqual("STALLED", st.one(".value").get("innerHTML"),
           "Chosen choicelist item is not displayed in HTML (value is '" +
           st.one(".value").get("innerHTML") + "')");
    }

}));

suite.add(new Y.Test.Case({

    name: 'choice_edit_non_clickable_content',

    setUp: setUp,

    tearDown: tearDown,

    make_config: function() {
        return {
            contentBox:  '#thestatus',
            value:       'incomplete',
            title:       'Change status to',
            items: [
              { name: 'New', value: 'new', style: '',
                help: '', disabled: false },
              { name: 'Invalid', value: 'invalid', style: '',
                help: '', disabled: true },
              { name: 'Incomplete', value: 'incomplete', style: '',
                help: '', disabled: false },
              { name: 'Fix Released', value: 'fixreleased', style: '',
                help: '', disabled: false },
              { name: 'Fix Committed', value: 'fixcommitted', style: '',
                help: '', disabled: true },
              { name: 'In Progress', value: 'inprogress', style: '',
                help: '', disabled: false },
              { name: 'Stalled', value: 'stalled', style: '',
                help: '', disabled: false, source_name: 'STALLED' }
            ],
            clickable_content: false
        };
    },

    test_clicking_content_doesnt_create_choicelist: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        Assert.isUndefined(this.choice_edit._choice_list,
          "ChoiceList object is created");
        Assert.isNull(Y.one(document).one(".yui3-ichoicelist"),
          "ChoiceList HTML is being added to the page");
    },

    test_clicking_icon_creates_choicelist: function() {
        simulate(this.choice_edit.get('boundingBox'), '.editicon', 'click');
        Assert.isNotUndefined(this.choice_edit._choice_list,
          "ChoiceList object is not being created");
        Assert.isNotNull(Y.one(document).one(".yui3-ichoicelist"),
          "ChoiceList HTML is not being added to the page");
    },

}));


/**
 * Tests what happens when config.value does not correspond to any of
 * the items in config.items.
 */
suite.add(new Y.Test.Case({

    name: 'choice_edit_value_item_mismatch',

    setUp: setUp,

    tearDown: tearDown,

    make_config: function() {
        return {
            contentBox:  '#thestatus',
            value:       null,
            title:       'Change status to',
            items: [
                { name: 'New', value: 'new', style: '',
                  help: '', disabled: false },
                { name: 'Invalid', value: 'invalid', style: '',
                  help: '', disabled: true }
            ]
        };
    },

    /**
     * The value displayed in the page should be left alone if
     * config.value does not correspond to any item in config.items.
     */
    test_choicesource_leaves_value_in_page: function() {
        var st = Y.one(document).one("#thestatus");
        Assert.areEqual(
            "Unset", st.one(".value").get("innerHTML"),
            "ChoiceSource is overriding displayed value in HTML");
    },

    test_choicelist_html_has_current: function() {
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        var configcount = this.config.items.length;
        var choicelist_lis = Y.one(document).all(".yui3-ichoicelist li");

        var that = this;
        var asserted;
        var test_li = function(li) {
            var text = li.get("text");
            for (var i=0; i < that.config.items.length; i++) {
                if (that.config.items[i].name == text) {
                    if (that.config.items[i].value == that.choice_edit.get("value")) {
                        Assert.isNotNull(li.one("span.current"),
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
        // Once a choice is made, the current value is marked with the
        // "current" class in the choice list.
        simulate(this.choice_edit._choice_list.get('boundingBox'),
            'li a[href$=new]', 'click');
        simulate(this.choice_edit.get('boundingBox'), '.value', 'click');
        asserted = false;
        choicelist_lis.refresh();
        choicelist_lis.each(test_li);
        Assert.isTrue(asserted, "There was no current LI item");
    }

}));

suite.add(new Y.Test.Case({

    name: 'nullable_choice_edit',

    setUp: function() {
      // add the in-page HTML
      var inpage = Y.Node.create([
        '<p id="nullchoiceedit" style="margin-top: 25px">',
        '  <img class="addicon" src="https://bugs.edge.launchpad.net/@@/add">',
        '  <span class="nulltext">Choose something</span>',
        '  <span class="value" style="display:none" />',
        '  <img class="editicon" style="display:none" src="https://bugs.edge.launchpad.net/@@/edit">',
        '</p>'].join(''));
      Y.one("body").appendChild(inpage);
      this.null_choice_edit = new Y.NullChoiceSource({
        contentBox:  '#nullchoiceedit',
        value:       null,
        title:       'Choose something',
        items: [
          { name: 'Chico', value: 'chico', style: '',
            help: '', disabled: false },
          { name: 'Harpo', value: 'harpo', style: '',
            help: '', disabled: false },
          { name: 'Groucho', value: 'groucho', style: '',
            help: '', disabled: false },
          { name: 'Gummo', value: 'gummo', style: '',
            help: '', disabled: false },
          { name: 'Zeppo', value: 'zeppo', style: '',
            help: '', disabled: false },
          { name: 'Not funny!', value: null, style: '',
            help: '', disabled: false }
        ]
      });

      this.null_choice_edit.render();
    },

    tearDown: function() {
        if (this.null_choice_edit._choice_list) {
            cleanup_widget(this.null_choice_edit._choice_list);
        }
        var nullchoiceedit = Y.one("document").one("#nullchoiceedit");
        if (nullchoiceedit) {
            nullchoiceedit.get("parentNode").removeChild(nullchoiceedit);
        }
    },

    test_can_be_instantiated: function() {
        Assert.isInstanceOf(
            Y.NullChoiceSource, this.null_choice_edit,
            "NullChoiceSource not instantiated.");
    },

    test_action_icon: function() {
        var that = this;

        Assert.areEqual(
            this.null_choice_edit.get('actionicon'),
            this.null_choice_edit.get('addicon'),
            'Action icon is not the add icon like expected.');

        Assert.areEqual(
            this.null_choice_edit.get('addicon').getStyle('display'),
            'inline',
            'Add icon is not visible when it should be');
        Assert.areEqual(
            this.null_choice_edit.get('editicon').getStyle('display'),
            'none',
            "Edit icon is visible when it shouldn't be");

        simulate(this.null_choice_edit.get('boundingBox'),
                 '.value', 'click');
        simulate(this.null_choice_edit._choice_list.get('boundingBox'),
          'li a[href$=groucho]', 'click');
        this.null_choice_edit._uiClearWaiting();

        Assert.areEqual(
            this.null_choice_edit.get('actionicon'),
            this.null_choice_edit.get('editicon'),
            'Action icon is not the add icon like expected.');
        Assert.areEqual(
            this.null_choice_edit.get('addicon').getStyle('display'),
            'none',
            "Add icon is visible when it shouldn't be");
        Assert.areEqual(
            this.null_choice_edit.get('editicon').getStyle('display'),
            'inline',
            "Edit icon is not visible when it shouldn be");
    },

    test_null_item_absent: function() {
        Assert.areEqual(
            this.null_choice_edit.get('value'),
            null,
            "Selected value isn't null");

        simulate(this.null_choice_edit.get('boundingBox'),
                 '.value', 'click');
        var remove_action_present = false;
        this.null_choice_edit._choice_list.get(
            'boundingBox').all('li a').each(function(item) {
            if (item._value == null) {
                remove_action_present = true;
            }
        });
        Assert.isFalse(
            remove_action_present,
            'Remove item is present even when the current value is null.');
    },

    test_get_input_for_null: function() {
        this.null_choice_edit.set('value', 'groucho');
        Assert.areEqual(
            'groucho',
            this.null_choice_edit.getInput(),
            "getInput() did not return the current value");
        // Simulate choosing a null value and check that getInput()
        // returns the new value.
        this.null_choice_edit.onClick({button: 1, halt: function(){}});
        this.null_choice_edit._choice_list.fire('valueChosen', null);
        Assert.areEqual(
            null,
            this.null_choice_edit.getInput(),
            "getInput() did not return the current (null) value");
    }
}));

Y.lp.testing.Runner.run(suite);

});
