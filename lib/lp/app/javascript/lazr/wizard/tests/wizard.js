/* Copyright (c) 2010, Canonical Ltd. All rights reserved. */

YUI().use('lazr.wizard', 'lazr.testing.runner',
          'lazr.testing.mockio', 'node', 'event', 'event-simulate',
          'dump', 'console', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.


/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var rawnode = Y.Node.getDOMNode(widget.one(selector));
    Y.Event.simulate(rawnode, evtype, options);
}

/* Helper function to cleanup and destroy a form wizard instance */
function cleanup_wizard(wizard) {
    if (wizard.get('rendered')) {
        var bb = wizard.get('boundingBox');
        if (Y.Node.getDOMNode(bb)){
            bb.get('parentNode').removeChild(bb);
        }
    }

    // Kill the widget itself.
    wizard.destroy();
}

/* Helper function that creates a new form wizard instance. */
function make_wizard(cfg) {
    var wizard = new Y.lazr.wizard.Wizard(cfg);
    wizard.render();
    return wizard;
}

/* Helper array of steps for creating a wizard */
var default_steps = [
    new Y.lazr.wizard.Step({
        form_content: "Hello."
    })
];

var suite = new Y.Test.Suite("Wizard Tests");

suite.add(new Y.Test.Case({

    name: 'wizard_basics',

    setUp: function() {
        wizard_steps = [
            new Y.lazr.wizard.Step({
                title: "Step One",
                form_content: [
                    'Here is an input: ',
                    '<input type="text" name="field1" id="field1" />',
                    'Here is another input: ',
                    '<input type="text" name="field2" id="field2" />'
                    ].join(""),
                funcLoad: function() {},
                funcCleanUp: function() {}
            })
            ]
        this.wizard = make_wizard({
            headerContent: 'Form for testing',
            steps: wizard_steps,
            xy: [0, 0]
        });

        // Ensure window size is constant for tests
        this.width = window.top.outerWidth;
        this.height = window.top.outerHeight;
        window.top.resizeTo(800, 600);
    },

    tearDown: function() {
        window.top.resizeTo(this.width, this.height);
        cleanup_wizard(this.wizard);
    },

    _should: {
        // The following tests will only be deemed to have passed if
        // they raise an error.
        error: {
            test_wizard_needs_steps: true,
            test_cant_go_back_when_at_first_step: true,
            test_cant_go_forward_when_at_last_step: true
        }
    },

    test_wizard_can_be_instantiated: function() {
        var wizard = new Y.lazr.wizard.Wizard({
            steps: default_steps
        });
        Assert.isInstanceOf(
            Y.lazr.wizard.Wizard,
            wizard,
            "Wizard could not be instantiated.");
        cleanup_wizard(wizard);
    },

    test_wizard_needs_steps: function() {
        // The wizard will raise an error if no steps are provided. Note
        // that this test will raise the error; this is expected
        // behaviour and is declared in the _should object, above.
        var wizard = new Y.lazr.wizard.Wizard();
        Assert.isInstanceOf(
            Y.lazr.wizard.Wizard,
            wizard,
            "Wizard could not be instantiated.");
        cleanup_wizard(wizard);
    },

    test_body_content_is_single_node: function() {
        Assert.areEqual(
            1,
            new Y.NodeList(this.wizard.getStdModNode("body")).size(),
            "The body content should be a single node, not a node list.");
    },

    test_form_content_in_body_content: function() {
        // The form_content should be included in the body of the
        // wizard during initialization.
        var body_content = this.wizard.getStdModNode("body");

        // Ensure the body_content contains our form node.
        Assert.isTrue(
            body_content.contains(this.wizard.form_node),
            "The form node is part of the body content.");

        // And then make sure that the user-supplied form_content is
        // included in the form node:
        Assert.areNotEqual(
            body_content.get("innerHTML").search(
                this.wizard.get("form_content")));
    },

    test_first_input_has_focus: function() {
        // The first input element in the form content should have
        // focus.
        var first_input = this.wizard.form_node.one('#field1');

        // Hide the wizard and ensure that the first input does not
        // have the focus.
        this.wizard.hide();
        first_input.blur();

        var test = this;
        var focused = false;

        var onFocus = function(e) {
            focused = true;
        };

        first_input.on('focus', onFocus);

        this.wizard.show();
        Assert.isTrue(focused,
            "The form wizard's first input field receives focus " +
            "when the wizard is shown.");
    },

    test_form_submit_in_body_content: function() {
        // The body content should include the submit button.
        var body_content = this.wizard.getStdModNode("body");
        Assert.isTrue(
            body_content.contains(
                this.wizard.get("form_submit_button")),
            "The body content includes the form_submit_button.");
    },

    test_users_submit_button_in_body_content: function() {
        // If a user supplies a custom submit button, it should be included
        // in the form instead of the default one.
        var submit_button = Y.Node.create(
            '<input type="submit" value="Hit me!" />');
        var wizard = new Y.lazr.wizard.Wizard({
            steps: [
                new Y.lazr.wizard.Step({
                    form_content: 'Here is an input: ' +
                        '<input type="text" name="field1" id="field1" />'
                })
            ],
            form_submit_button: submit_button
        });
        wizard.render();

        // Ensure the button has been used in the form:
        Assert.isTrue(
            wizard.form_node.contains(submit_button),
            "The form should include the users submit button.");

        cleanup_wizard(wizard);
    },

    test_form_cancel_in_body_content: function() {
        // The body content should include the cancel button.
        var body_content = this.wizard.getStdModNode("body");
        Assert.isTrue(
            body_content.contains(
                this.wizard.get("form_cancel_button")),
            "The body content includes the form_cancel_button.");
    },

    test_users_cancel_button_in_body_content: function() {
        // If a user supplies a custom cancel button, it should be included
        // in the form instead of the default one.
        var cancel_button = Y.Node.create(
            '<button type="" value="cancel" />');
        var wizard = new Y.lazr.wizard.Wizard({
            steps: [
                new Y.lazr.wizard.Step({
                    form_content: 'Here is an input: ' +
                        '<input type="text" name="field1" id="field1" />'
                })
            ],
            form_cancel_button: cancel_button
        });
        wizard.render();

        // Ensure the button has been used in the form:
        Assert.isTrue(
            wizard.form_node.contains(cancel_button),
            "The form should include the users cancel button.");

        cleanup_wizard(wizard);
    },

    test_hide_when_cancel_clicked: function() {
        // The form wizard should hide when the cancel button is clicked.

        var bounding_box = this.wizard.get('boundingBox');
        Assert.isFalse(
            bounding_box.hasClass('yui3-lazr-wizard-hidden'),
            "The form is not hidden initially.");

        simulate(
            this.wizard.form_node,
            "button[type=button]",
            'click');

        Assert.isTrue(
            bounding_box.hasClass('yui3-lazr-wizard-hidden'),
            "The form is hidden after cancel is clicked.");
    },

    test_error_displayed_on_showError: function() {
        // The error message should be in the body content.

        this.wizard.showError("My special error");

        var body_content = this.wizard.getStdModNode("body");
        Assert.areNotEqual(
            body_content.get("innerHTML").search("My special error"),
            -1,
            "The error text was included in the body content.");
    },

    test_tags_stripped_from_errors: function() {
        // Any tags in error messages will be stripped out.
        // That is, as long as they begin and end with ASCII '<' and '>'
        // chars. Not sure what to do about unicode, for example.
        this.wizard.showError("<h2>My special error</h2>");

        var body_content = this.wizard.getStdModNode("body");
        Assert.areEqual(
            -1,
            body_content.get("innerHTML").search("<h2>"),
            "The tags were stripped from the error message.");
    },

    test_error_cleared_on_clearError: function() {
        // The error message should be cleared from the body content.
        this.wizard.showError("My special error");
        this.wizard.clearError();
        var body_content = this.wizard.getStdModNode("body");
        Assert.areEqual(
            body_content.get("innerHTML").search("My special error"),
            -1,
            "The error text is cleared from the body content.");
    },

    test_wizard_centered_when_shown: function() {
        // If the 'centered' attribute is set, the wizard should be
        // centered in the viewport when shown.
        Assert.areEqual('[0, 0]', Y.dump(this.wizard.get('xy')),
                        "Position is initially 0,0.");
        this.wizard.show();
        Assert.areEqual('[0, 0]', Y.dump(this.wizard.get('xy')),
                        "Position is not updated if widget not centered.");
        this.wizard.hide();

        this.wizard.set('centered', true);
        this.wizard.show();
        var centered_pos_before_resize = this.wizard.get('xy');
        Assert.areNotEqual('[0, 0]', Y.dump(centered_pos_before_resize),
                           "Position is updated when centered attr set.");
        this.wizard.hide();

        var centered = false;
        function watch_centering() {
            centered = true;
        }
        Y.Do.after(watch_centering, this.wizard, 'centered');

        // The position is updated after resizing the window and re-showing:
        window.top.resizeTo(850, 550);
        this.wizard.show();

        Assert.isTrue(centered,
            "The wizard centers itself when it is shown with the centered " +
            "attribute set.");
    },

    test_form_content_as_node: function() {
        // The form content can also be passed as a node, rather than
        // a string of HTML.
        var form_content_div = Y.Node.create("<div />");
        var input_node = Y.Node.create(
            '<input type="text" name="field1" value="val1" />');
        form_content_div.appendChild(input_node);

        var wizard = make_wizard({
            headerContent: 'Form for testing',
            steps: [
                new Y.lazr.wizard.Step({
                    form_content: form_content_div
                })
            ]
        });

        Assert.isTrue(
            wizard.form_node.contains(input_node),
            "Failed to pass the form content as a Y.Node instance.");
        cleanup_wizard(wizard);
    },

    test_first_step_load_called_on_wizard_load: function() {
        // The load() function of the first step will be called when the
        // wizard is instantiated.
        var load_called = false;
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here.",
                funcLoad: function() {
                    load_called = true;
                }
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();

        Assert.isTrue(
            load_called,
            "The funcLoad callback of the first step was not called.");
    },

    test_step_load_called_on_wizard_next: function() {
        // When wizard.next() is called, the next Step's funcLoad
        // callback will be called.
        var load_called = false;
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            }),
            new Y.lazr.wizard.Step({
                form_content: "Still nothing to see here.",
                funcLoad: function() {
                    load_called = true;
                }
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();
        wizard.next();

        Assert.isTrue(
            load_called,
            "The funcLoad callback of the next step was not called.");
    },

    test_step_load_called_on_wizard_prev: function() {
        // When wizard.previous() is called, the previous Step's funcLoad
        // callback will be called.
        var load_called = false;
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here.",
                funcLoad: function() {
                    load_called = true;
                }
            }),
            new Y.lazr.wizard.Step({
                form_content: "Still nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();
        wizard.next();
        load_called = false;
        wizard.previous();

        Assert.isTrue(
            load_called,
            "The funcLoad callback of the first step was not called.");
    },

    test_cant_go_back_when_at_first_step: function() {
        // When a wizard is on its first step, calling wizard.previous()
        // will raise an error.
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();
        wizard.previous();
    },

    test_cant_go_forward_when_at_last_step: function() {
        // When a wizard is on its last step, calling wizard.next()
        // will raise an error.
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();
        wizard.next();
    },

    test_hasNextStep_returns_true_with_next_step: function() {
        // Wizard.hasNextStep() will return True if there are more
        // steps after the current one.
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            }),
            new Y.lazr.wizard.Step({
                form_content: "Still nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();

        Assert.isTrue(
            wizard.hasNextStep(),
            "Wizard.hasNextStep() should return true.");
    },

    test_hasNextStep_returns_false_with_no_next_step: function() {
        // Wizard.hasNextStep() will return false if there are no more
        // steps after the current one.
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();

        Assert.isFalse(
            wizard.hasNextStep(),
            "Wizard.hasNextStep() should return false.");
    },

    test_hasPreviousStep_returns_true_with_prev_step: function() {
        // Wizard.hasPreviousStep() will return True if there are steps
        // before the current one.
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            }),
            new Y.lazr.wizard.Step({
                form_content: "Still nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();
        wizard.next();

        Assert.isTrue(
            wizard.hasPreviousStep(),
            "Wizard.hasPreviousStep() should return true.");
    },

    test_hasPreviousStep_returns_false_with_no_prev_step: function() {
        // Wizard.hasPreviousStep() will return false if there are no
        // steps before the current one.
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();

        Assert.isFalse(
            wizard.hasPreviousStep(),
            "Wizard.hasPreviousStep() should return false.");
   },

   test_stepChange_fired_on_step_change: function() {
        // Changing the step will fire a wizard:stepChange event.
        var stepChange_fired = false;
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            }),
            new Y.lazr.wizard.Step({
                form_content: "Still nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.on("wizard:stepChange", function() {
            stepChange_fired = true;
        });
        wizard.render();
        wizard.next();

        Assert.isTrue(
            stepChange_fired, "wizard:stepChange did not fire.");
   },

   test_addStep_adds_step: function() {
        // Wizard.addStep() adds a step to the Wizard.
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();
        // There's only one step at this point, so hasNextStep() returns
        // False.
        Assert.isFalse(
            wizard.hasNextStep(),
            "Wizard.hasNextStep() should return false.");
        wizard.addStep(new Y.lazr.wizard.Step({
            form_content: "Still nothing. Move along."
        }));
        Assert.isTrue(
            wizard.hasNextStep(),
            "Wizard.hasNextStep() should return true.");
   },

   test_destructor_deletes_steps: function() {
        // Wizard.destructor() deletes all the of the Wizard's Steps.
        var wizard_steps = [
            new Y.lazr.wizard.Step({
                form_content: "Nothing to see here."
            })
        ]
        var wizard = make_wizard({
            steps: wizard_steps
        });
        wizard.render();
        wizard.destructor();

        var steps = wizard.get("steps");
        Assert.areEqual(
            0, steps.length, "There should be no steps left.");
   }


}));

suite.add(new Y.Test.Case({

    name: 'wizard_data',

    test_submit_callback_called_on_submit: function() {
        // Set an expectation that the form_submit_callback will be
        // called with the correct data:
        var callback_called = false;
        var submit_callback = function(ignore){
            callback_called = true;
        };
        var wizard = make_wizard({
            steps: [
                new Y.lazr.wizard.Step({
                    form_content:
                        '<input type="text" name="field1" value="val1" />',
                })
            ],
            form_submit_callback: submit_callback
        });
        simulate(
            wizard.form_node,
            "input[type=submit]",
            'click');

        Assert.isTrue(
            callback_called,
            "The form_submit_callback should be called.");
        cleanup_wizard(wizard);
    },

    test_submit_with_callback_prevents_propagation: function() {
        // The onsubmit event is not propagated when user provides
        // a callback.

        var wizard = make_wizard({
            steps: [
                new Y.lazr.wizard.Step({
                    form_content:
                        '<input type="text" name="field1" value="val1" />',
                })
            ],
            form_submit_callback: function() {}
        });

        var event_was_propagated = false;
        var test = this;
        var onSubmit = function(e) {
            event_was_propagated = true;
            e.preventDefault();
        };
        Y.on('submit', onSubmit, wizard.form_node);

        simulate(wizard.form_node, "input[type=submit]", 'click');

        Assert.isFalse(
            event_was_propagated,
            "The onsubmit event should not be propagated.");
        cleanup_wizard(wizard);
    },

    test_submit_without_callback: function() {
        // The form should submit as a normal form if no callback
        // was provided.
        var wizard = make_wizard({
            steps: [
                new Y.lazr.wizard.Step({
                    form_content:
                        '<input type="text" name="field1" value="val1" />',
                })
            ],
        });

        var event_was_propagated = false;
        var test = this;
        var onSubmit = function(e) {
            event_was_propagated = true;
            e.preventDefault();
        };

        Y.on('submit', onSubmit, wizard.form_node);

        simulate(
            wizard.form_node,
            "input[type=submit]",
            'click');
        Assert.isTrue(event_was_propagated,
                      "The normal form submission event is propagated as " +
                      "normal when no callback is provided.");
        cleanup_wizard(wizard);
    },

    test_getFormData_returns_correct_data_for_simple_inputs: function() {
        // The getFormData method should return the values of simple
        // inputs correctly.

        var wizard = make_wizard({
            headerContent: 'Form for testing',
            steps: [
                new Y.lazr.wizard.Step({
                    form_content: [
                        'Here is an input: ',
                        '<input type="text" name="field1" value="val1" />',
                        '<input type="text" name="field2" value="val2" />',
                        '<input type="text" name="field3" value="val3" />'
                        ].join("")
                })
            ],
        });
        Assert.areEqual(
            '{field1 => [val1], field2 => [val2], field3 => [val3]}',
            Y.dump(wizard.getFormData()),
            "The getFormData method returns simple input data correctly.");
        cleanup_wizard(wizard);
    },

    test_getFormData_returns_inputs_nested_several_levels: function() {
        // The getFormData method should return the values of inputs
        // even when they are several levels deep in the form node
        var wizard = make_wizard({
            headerContent: 'Form for testing',
            steps: [
                new Y.lazr.wizard.Step({
                    form_content: [
                        'Here is an input: ',
                        '<div>',
                        '  <input type="text" name="field1" value="val1" />',
                        '  <div>',
                        '    <input type="text" name="field2" value="val2" ',
                        '    />',
                        '    <div>',
                        '      <input type="text" name="field3" ',
                        '        value="val3" />',
                        '    </div>',
                        '  </div>',
                        '</div>'
                    ].join("")
                })
            ]
        });

        Assert.areEqual(
            '{field1 => [val1], field2 => [val2], field3 => [val3]}',
            Y.dump(wizard.getFormData()),
            "The getFormData method returns simple input data correctly.");
        cleanup_wizard(wizard);

    },

}));

Y.lazr.testing.Runner.add(suite);
Y.lazr.testing.Runner.run();

});
