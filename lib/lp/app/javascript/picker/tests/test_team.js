/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI.add('lp.app.picker.team.test', function (Y) {
    var tests = Y.namespace('lp.app.picker.team.test');
    tests.suite = new Y.Test.Suite(
        'lp.app.picker.team Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.app.picker.team_tests',


        setUp: function() {
        },

        tearDown: function() {
            delete this.mockio;
            if (this.fixture !== undefined) {
                this.fixture.empty(true);
            }
            delete this.fixture;
            var ns = Y.namespace('lp.app.picker.team');
            ns.widgets = null;
            ns.team_form = null;
        },

        _simple_team_form: function() {
            return '<table><tr><td>' +
                '<input id="field.name" name="field.name"/>' +
                '<input id="field.displayname" ' +
                'name="field.displayname"/></td></tr></table>';
        },

        create_widget: function() {
            this.mockio = new Y.lp.testing.mockio.MockIo();
            this.widget = new Y.lp.app.picker.team.CreateTeamForm({
                "io_provider": this.mockio
            });
            Y.Assert.areEqual(
                'file:////people/+simplenewteam/++form++',
                this.mockio.last_request.url);
            this.mockio.success({
                responseText: this._simple_team_form(),
                responseHeaders: {'Content-Type': 'text/html'}});
            this.fixture = Y.one('#fixture');
            this.fixture.appendChild(this.widget.get('container'));
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.app.picker.team,
                "Could not locate the lp.app.team module");
        },

        test_widget_can_be_instantiated: function() {
            this.create_widget();
            Y.Assert.isInstanceOf(
                Y.lp.app.picker.team.CreateTeamForm, this.widget,
                "Create Team Form failed to be instantiated");
        },

        test_new_team_save: function() {
            // Clicking the save button on the new team form creates the team.
            this.create_widget();

            var save_success_called = false;
            this.widget._save_team_success = function(response, team_data) {
                Y.Assert.areEqual('fred', team_data['field.name']);
                save_success_called = true;
            };
            var team_name = Y.one("input[id='field.name']");
            team_name.set('value', 'fred');
            var form_buttons = Y.one('.extra-form-buttons');
            form_buttons.one('button.yes_button').simulate('click');
            this.mockio.success({
                responseText: '',
                responseHeaders: {'Content-Type': 'application/json'}});
            Y.Assert.isTrue(save_success_called);
        },

        test_save_team_success: function() {
            // The save team success callback publishes the expected event and
            // clears the form.
            this.create_widget();
            var event_publishd = false;
            this.widget.subscribe(Y.lp.app.picker.team.TEAM_CREATED,
                function(e) {
                    var data = e.details[0];
                    Y.Assert.areEqual('fred', data.value);
                    Y.Assert.areEqual('Fred', data.title);
                    Y.Assert.areEqual('/~fred', data.api_uri);
                    Y.Assert.areEqual('team', data.metadata);
                    event_publishd = true;
                });
            var ns = Y.namespace('lp.app.picker.team');
            ns.team_form = '<p>test</p>';
            var team_data = {
                'field.name': 'fred',
                'field.displayname': 'Fred'
            };
            this.widget._save_team_success('', team_data);
            Y.Assert.isTrue(event_publishd);
            Y.Assert.areEqual('test', Y.one('form p').get('text'));
        }
    }));

}, '0.1', {
    'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.client', 'lp.testing.mockio', 'lp.app.picker.team']
});