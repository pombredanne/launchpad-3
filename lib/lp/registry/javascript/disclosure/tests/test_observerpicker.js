/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.registry.disclosure.observerpicker.test', function (Y) {

    var tests = Y.namespace('lp.registry.disclosure.observerpicker.test');
    tests.suite = new Y.Test.Suite('lp.registry.disclosure.observerpicker Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.registry.disclosure.observerpicker_tests',

        setUp: function () {
            this.vocabulary = [
                {"value": "fred", "title": "Fred", "css": "sprite-person",
                    "description": "fred@example.com", "api_uri": "~/fred",
                    "metadata": "person"},
                {"value": "frieda", "title": "Frieda", "css": "sprite-team",
                    "description": "frieda@example.com", "api_uri": "~/frieda",
                    "metadata": "team"}
            ];
            this.access_policies = [
                {index: '0', value: 'P1', title: 'Policy 1',
                 description: 'Policy 1 description'},
                {index: '1', value: 'P2', title: 'Policy 2',
                 description: 'Policy 2 description'},
                {index: '2', value: 'P3', title: 'Policy 3',
                 description: 'Policy 3 description'}];
        },

        tearDown: function () {
            if (Y.Lang.isObject(this.picker)) {
                this.cleanup_widget(this.picker);
            }
        },

        /* Helper function to clean up a dynamically added widget instance. */
        cleanup_widget: function(widget) {
            // Nuke the boundingBox, but only if we've touched the DOM.
            if (widget.get('rendered')) {
                var bb = widget.get('boundingBox');
                bb.get('parentNode').removeChild(bb);
            }
            // Kill the widget itself.
            widget.destroy();
        },

        _create_picker: function(overrides) {
            var config = {
                anim_duratrion: 0,
                progressbar: true,
                progress: 50,
                headerContent: "<h2>Grant access</h2>",
                steptitle: "Search for user or exclusive team " +
                            "with whom to share",
                zIndex: 1000,
                visible: false,
                access_policies: this.access_policies
            };
            if (overrides !== undefined) {
                config = Y.merge(config, overrides);
            }
            var picker =
                new Y.lp.registry.disclosure.observerpicker.ObserverPicker(config);
            Y.lp.app.picker.setup_vocab_picker(picker, "TestVocab", config);
            return picker;
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.disclosure.observerpicker,
                "We should be able to locate the " +
                "lp.registry.disclosure module");
        },

        test_picker_can_be_instantiated: function() {
            this.picker = this._create_picker();
            Y.Assert.isInstanceOf(
                Y.lp.registry.disclosure.observerpicker.ObserverPicker,
                this.picker,
                "Picker failed to be instantiated");
        },

        // Test that the picker initially displays a normal search and select
        // facility and transitions to step two when a result is selected.
        test_first_step: function() {
            this.picker = this._create_picker();
            // Select a person to trigger transition to next step.
            this.picker.set('results', this.vocabulary);
            this.picker.render();
            var cb = this.picker.get('contentBox');
            var steptitle = cb.one('.contains-steptitle h2').getContent();
            Y.Assert.areEqual(
                'Search for user or exclusive team with whom to share',
                steptitle);
            this.picker.get('boundingBox').one(
                '.yui3-picker-results li:nth-child(1)').simulate('click');
            // There should be no saved value at this stage.
            Y.Assert.isUndefined(this.saved_picker_value);

            // The progress should be 75%
            Y.Assert.areEqual(75, this.picker.get('progress'));
            // The first step ui should be hidden.
            Y.Assert.isTrue(cb.one('.yui3-widget-bd').hasClass('unseen'));
            // The step title should be updated according to the selected
            // person.
            steptitle = cb.one('.contains-steptitle h2').getContent();
            Y.Assert.areEqual('Select access policy for Fred', steptitle);
            // The second step ui should be visible.
            var step_two_content = cb.one('.picker-content-two');
            Y.Assert.isFalse(step_two_content.hasClass('unseen'));
            // The second step ui should contain input buttons for each access
            // policy type.
            Y.Array.each(this.access_policies, function(policy) {
                var rb = step_two_content.one(
                    'input[value="' + policy.title + '"]');
                Y.Assert.isNotNull(rb);
            });
            // There should be a link back to previous step.
            Y.Assert.isNotNull(step_two_content.one('a.prev'));
            // There should be a button and link to finalise the selection.
            Y.Assert.isNotNull(step_two_content.one('a.next'));
            Y.Assert.isNotNull(step_two_content.one('button.next'));
        },

        // Test that the back link goes back to step one when step two is
        // active.
        test_second_step_back_link: function() {
            this.picker = this._create_picker();
            // Select a person to trigger transition to next step.
            this.picker.set('results', this.vocabulary);
            this.picker.render();
            this.picker.get('boundingBox').one(
                '.yui3-picker-results li:nth-child(1)').simulate('click');
            var cb = this.picker.get('contentBox');
            var step_two_content = cb.one('.picker-content-two');
            var back_link = step_two_content.one('a.prev');
            back_link.simulate('click');
            // The progress should be 50%
            Y.Assert.areEqual(50, this.picker.get('progress'));
            // The first step ui should be visible.
            Y.Assert.isFalse(cb.one('.yui3-widget-bd').hasClass('unseen'));
            // The step title should be updated.
            var steptitle = cb.one('.contains-steptitle h2').getContent();
            Y.Assert.areEqual(
                'Search for user or exclusive team with whom to share',
                steptitle);
            // The second step ui should be hidden.
            Y.Assert.isTrue(step_two_content.hasClass('unseen'));
        },

        // Test that a selection made in step two is correctly passed to the
        // specified save function.
        test_second_step_final_selection: function() {
            var selected_result;
            this.picker = this._create_picker(
                {
                    save: function(result) {
                        selected_result = result;
                    }
                }
            );
            // Select a person to trigger transition to next step.
            this.picker.set('results', this.vocabulary);
            this.picker.render();
            this.picker.get('boundingBox').one(
                '.yui3-picker-results li:nth-child(1)').simulate('click');
            var cb = this.picker.get('contentBox');
            var step_two_content = cb.one('.picker-content-two');
            // Select an access policy.
            step_two_content.one('input[value="Policy 2"]').simulate('click');
            var select_link = step_two_content.one('a.next');
            select_link.simulate('click');
            Y.ArrayAssert.itemsAreEqual(
                ['Policy 2'], selected_result.access_policies);
            Y.Assert.areEqual('~/fred', selected_result.api_uri);
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.app.picker', 'lp.registry.disclosure.observerpicker']});
