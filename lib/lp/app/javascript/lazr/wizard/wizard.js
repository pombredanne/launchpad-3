/* Copyright (c) 2010, Canonical Ltd. All rights reserved.
 *
 * Display a functioning form in a lazr.formoverlay.
 *
 * @module lazr.wizard
 */
YUI.add('lazr.wizard', function(Y) {

    var namespace = Y.namespace("lazr.wizard");

   /**
    * The Step class isn't so much a Widget as it is just an Object with
    * references to perform certain functions. They are used to tell the
    * Wizard what to do next.
    *
    * @class Step
    * @namespace lazr.wizard
    */
    function Step(config) {
        Step.superclass.constructor.apply(this, arguments);
    }
    Step.NAME = "step";
    Step.ATTRS = {
        title: {
            value: ''
        },
        form_content: {
            value: null
        },
        funcLoad: {
            value: function() {}
        },
        funcCleanUp: {
            value: function() {}
        }
    };

    Y.extend(Step, Y.Widget, {
        load: function() {
            this.get("funcLoad").apply(this, arguments);
        }
    });
    namespace.Step = Step;


   /**
    * The Wizard class builds on the lazr.FormOverlay class
    * to display form content and extract form data for the callsite.
    *
    * @class Wizard
    * @namespace lazr.wizard
    */
    function Wizard(config) {
        Wizard.superclass.constructor.apply(this, arguments);

        if (this.get("steps").length == 0) {
            throw "Cannot create a Wizard with no steps.";
        }
        Y.after(this._renderUIWizard, this, "renderUI");
        Y.after(this._bindUIWizard, this, "bindUI");
    }

    Wizard.NAME = "lazr-wizard";
    Wizard.ATTRS = {
        current_step_index: {
            value: -1
        },
        previous_step_index: {
            value: -1
        },
        next_step_index: {
            value: 0
        },
        steps: {
            value: []
        }
    }

    Y.extend(Wizard, Y.lazr.FormOverlay, {

        initializer: function() {
            /* Do nothing */
        },

        _renderUIWizard: function() {
            this.next();
        },

        _bindUIWizard: function() {
            Y.on("click",
                Y.bind(function(e){ this.hide();}, this),
                this.get("form_cancel_button"));
        },

        /**
         * Add a step to the end of the steps array.
         *
         * @method addStep
         */
        addStep: function(step) {
            this.get("steps").push(step);
            // If the widget is currently on its final step, update the
            // next_step_index to reflect the fact that we've just added
            // a new one.
            if (!this.hasNextStep()) {
                var current_step_index = this.get("current_step_index");
                this.set("next_step_index", current_step_index + 1);
            }
        },

        /**
         * Transition to the step at a given index.
         *
         * @method _transitionToStep
         * @private
         * @param step_index The index of the step to transition to.
         */
        _transitionToStep: function(step_index) {
            var step = this.get("steps")[step_index];
            this.set("steptitle", step.get("title"));

            var step_form_content = step.get("form_content");
            if (Y.Lang.isValue(step_form_content)) {
                this.set("form_content", step_form_content);
                this._setFormContent()
            }

            step.load(this);
            this.fire("wizard:stepChange");
            this.set("current_step", step);
            this._updateStepIndices(step_index);
        },

        /**
         * Transition to the next step in the steps array.
         *
         * @method next
         */
        next: function() {
            var step_index = this.get("next_step_index");
            if (step_index < 0) {
                throw "Wizard is already on its last step.";
            }
            this._transitionToStep(step_index);
        },

        /**
         * Transition to the previous step in the steps array.
         *
         * @method next
         */
        previous: function() {
            var step_index = this.get("previous_step_index");
            if (step_index < 0) {
                throw "Wizard is already on its first step.";
            }
            this._transitionToStep(step_index);
        },

        /**
         * Update the step indices based on the current step index.
         *
         * @method _updateStepIndices
         * @private
         * @param current_step_index The index of the current step.
         */
        _updateStepIndices: function(current_step_index) {
            if (current_step_index > 0) {
                this.set("previous_step_index", current_step_index - 1);
            } else {
                this.set("previous_step_index", -1);
            }

            if (this.get("steps").length > current_step_index + 1) {
                this.set("next_step_index", current_step_index + 1);
            } else {
                this.set("next_step_index", -1);
            }

            this.set("current_step_index", current_step_index + 1);
        },

        /**
         * Return true if there's another step after the current one.
         *
         * @method hasNextStep
         */
        hasNextStep: function() {
            var next_step_index = this.get("next_step_index");
            return (next_step_index > 0)
        },

        /**
         * Return true if there's a step before the current one.
         *
         * @method hasPreviousStep
         */
        hasPreviousStep: function() {
            var previous_step_index = this.get("previous_step_index");
            return (previous_step_index > -1)
        },

        /**
         * Destroy all the Steps of the widget.
         *
         * @method destructor
         */
        destructor: function() {
            // Loop over all the steps and delete them.
            while(this.get("steps").length > 0) {
                var step = this.get("steps").pop();
                delete step;
            }
        }

    });

    namespace.Wizard = Wizard;

}, "0.1", {"skinnable": true, "requires": ["lazr.formoverlay"]});
