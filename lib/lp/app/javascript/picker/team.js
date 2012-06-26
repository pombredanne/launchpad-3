/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @namespace Y.app.picker.team
 * @requires lazr.picker, lazr.person-picker
 */
YUI.add('lp.app.picker.team', function(Y) {

var ns = Y.namespace('lp.app.picker.team');
var
    NAME = "createTeamWidget",
    // Events
    TEAM_CREATED = 'teamCreated',
    CANCEL_TEAM = 'cancelTeam';

ns.TEAM_CREATED = TEAM_CREATED;
ns.CANCEL_TEAM = CANCEL_TEAM;

ns.CreateTeamForm = Y.Base.create(NAME, Y.Base, [], {
    initializer: function(cfg) {
        this.publish(TEAM_CREATED);
        this.publish(CANCEL_TEAM);
        // We need to provide the 'New team' link functionality.
        // There could be several pickers and we only want to make the XHR
        // call to get the form once. So first one gets to do the call and
        // subsequent ones register the to be notified of the result.
        this.get('new_team_form').appendChild(this._new_team_template());
        this.team_form_error_handler =
            new Y.lp.client.FormErrorHandler({
                form: this.get('new_team_form')
            });
        this.form_namespace = Y.namespace('lp.app.picker.teamform');
        var form_callbacks = this.form_namespace.form_callbacks;
        var perform_load = false;
        if (!Y.Lang.isArray(form_callbacks)) {
            perform_load = true;
            form_callbacks = [];
            this.form_namespace.form_callbacks = form_callbacks;
        }
        form_callbacks.push({
            widget: this,
            callback: this._render_new_team_form});
        this._load_new_team_form(perform_load);
    },

    _new_team_template: function() {
        return [
          '<div id=new-team-form-placeholder ',
              'class="yui3-overlay-indicator-content">',
              '<img src="/@@/spinner-big/">',
          '</div>',
          '<div class="extra-form-buttons hidden">',
              '<button class="yes_button" type="submit" ',
              'name="field.actions.create" value="Create Team">',
              'Create Team</button>',
              '<button class="no_button" type="button">Cancel</button>',
            '</div>',
          '</div>'].join('');
    },

    _load_new_team_form: function (perform_load) {
        // Load the new team form from the model using an XHR call.
        // If perform_load is true, this is the first invocation of this method
        // across all pickers so we do the XHR call and send the result to all
        // registered pickers.
        // If perform_load is false, another picker is making the XNR call and
        // all we want to do is receive and render the preloaded_team_form.
        // We first check though that the result hasn't arrived already.
        var preloaded_team_form = this.form_namespace.team_form;
        if (Y.Lang.isValue(preloaded_team_form)) {
            this._render_new_team_form(preloaded_team_form, true);
            return;
        }
        if (!perform_load) {
            return;
        }

        var on_success = function(id, response, widget) {
            widget.form_namespace.team_form = response.responseText;
            Y.Array.each(widget.form_namespace.form_callbacks,
                function(callback_info) {
                Y.bind(
                    callback_info.callback, callback_info.widget,
                    response.responseText, true, callback_info.widget)();
            });
        };
        var on_failure = function(id, response, widget) {
            Y.Array.each(widget.form_namespace.form_callbacks,
                function(callback_info) {
                Y.bind(
                    callback_info.callback, callback_info.widget,
                    'Sorry, an error occurred while loading the form.',
                    false)();
            });
        };
        var cfg = {
            on: {success: on_success, failure: on_failure},
            "arguments": this
            };
        var uri = Y.lp.client.get_absolute_uri(
            'people/+simplenewteam/++form++');
        uri = uri.replace('api/devel', '');
        this.get("io_provider").io(uri, cfg);
    },

    _render_new_team_form: function(form_html, show_submit, widget) {
        // Poke the actual team form into the DOM and wire up the save and
        // cancel buttons.
        var new_team_form = this.get('new_team_form');
        new_team_form.one('#new-team-form-placeholder').replace(form_html);
        var submit_button = new_team_form.one(".yes_button");
        if (show_submit) {
            new_team_form.on('submit', function(e) {
                    e.halt();
                    this._save_new_team();
                }, this);
        } else {
            submit_button.addClass('hidden');
        }
        new_team_form.one(".no_button")
            .on('click', function(e) {
                e.halt();
                this.fire(CANCEL_TEAM);
            }, this);
        new_team_form.one('.extra-form-buttons').removeClass('hidden');
        this.show();
    },

    show: function() {
        var form_elements = this.get('new_team_form').get('elements');
        if (form_elements.size() > 0) {
            form_elements.item(0).focus();
        }
    },

    hide: function() {
        this.team_form_error_handler.clearFormErrors();
    },

    /**
     * Show the submit spinner.
     *
     * @method _showSubmitSpinner
     */
    _showSubmitSpinner: function(submit_link) {
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Creating..." />');
        submit_link.insert(spinner_node, 'after');
    },

    /**
     * Hide the submit spinner.
     *
     * @method _hideSubmitSpinner
     */
    _hideSubmitSpinner: function(submit_link) {
        var spinner = submit_link.get('parentNode').one('.spinner');
        if (spinner !== null) {
            spinner.remove(true);
        }
    },

    _save_new_team: function() {
        var submit_link = Y.one("[name='field.actions.create']");
        this.team_form_error_handler.showError =
            Y.bind(function (error_msg) {
                this._hideSubmitSpinner(submit_link);
                    this.team_form_error_handler.handleFormValidationError(
                        error_msg, [], []);
            }, this);

        var uri = Y.lp.client.get_absolute_uri('people/+simplenewteam');
        uri = uri.replace('api/devel', '');
        var form_data = {};
        var new_team_form = this.get('new_team_form');
        new_team_form.all("[name^='field.']").each(function(field) {
            form_data[field.get('name')] = field.get('value');
        });
        form_data.id = new_team_form;
        var y_config = {
            method: "POST",
            headers: {'Accept': 'application/json;'},
            on: {
                start: Y.bind(function() {
                    this.team_form_error_handler.clearFormErrors();
                    this._showSubmitSpinner(submit_link);
                }, this),
                end:
                    Y.bind(this._hideSubmitSpinner, this, submit_link),
                failure: this.team_form_error_handler.getFailureHandler(),
                success:
                    Y.bind(
                        function(id, response, team_data) {
                            var value = {
                                "api_uri": "/~" + team_data['field.name'],
                                "title": team_data['field.dispayname'],
                                "value": team_data['field.name'],
                                "metadata": "team"};
                            this.fire(TEAM_CREATED, value);
                        }, this)
            },
            'arguments': form_data
        };
        y_config.form = form_data;
        this.get("io_provider").io(uri, y_config);
    }
}, {
    ATTRS: {
        /**
         * The form used to enter the new team details.
         */
        new_team_form: {
            valueFn: function() {return Y.Node.create('<form/>');}
        },
        /**
        * The object that provides the io function for doing XHR requests.
        *
        * @attribute io_provider
        * @type object
        * @default Y
        */
        io_provider: {value: Y}
    }
});


}, "0.1", {"requires": [
    "base", "node", "lazr.picker", "lazr.person-picker"]});

