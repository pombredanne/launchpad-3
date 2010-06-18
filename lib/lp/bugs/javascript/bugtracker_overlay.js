/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * A bugtracker form overlay that can create a bugtracker within any page.
 *
 * @namespace Y.lp.bugs.bugtracker_overlay
 * @requires  dom, node, io-base, lazr.anim, lazr.formoverlay
 */
YUI.add('lp.bugs.bugtracker_overlay', function(Y) {
    Y.log('loading lp.bugs.bugtracker_overlay');
    var namespace = Y.namespace('lp.bugs.bugtracker_overlay');

    var bugtracker_form;
    var next_step;

    var save_new_bugtracker = function(data) {

        var parameters = {
            bug_tracker_type: data['field.bugtrackertype'][0],
            name: data['field.name'][0].toLowerCase(),
            title: data['field.title'][0],
            base_url: data['field.baseurl'][0],
            summary: data['field.summary'][0],
            contact_details: data['field.contactdetails'][0]
        };

        var finish_new_bugtracker = function(entry) {
            bugtracker_form.clearError();
            bugtracker_form.hide();
            // Reset the HTML form inside the widget.
            bugtracker_form.get('contentBox').one('form').reset();
            // Fill in the text field with either the name of the newly
            // created bug tracker or the name of an existing bug
            // tracker whose base_url matches.
            var bugtracker_text_box = Y.one(
                Y.DOM.byId('field.bugtracker.bugtracker'));
            bugtracker_text_box.set('value', entry.get('name'));
        };

        var client = new LP.client.Launchpad();
        client.named_post('/bugs/bugtrackers', 'ensureBugTracker', {
            parameters: parameters,
            on: {
                success: finish_new_bugtracker,
                failure: function (ignore, response, args) {
                    var error_box = Y.one('#bugtracker-error');
                    var error_message = response.statusText + '\n\n' +
                                        response.responseText;
                    bugtracker_form.showError(error_message);
                    // XXX: This should be done by FormOverlay.showError().
                    bugtracker_form.error_node.scrollIntoView();
                }
            }
        });
    };


    var setup_bugtracker_form = function () {
        var form_submit_button = Y.Node.create(
            '<input type="submit" name="field.actions.register" ' +
            'id="formoverlay-add-bugtracker" value="Create Milestone"/>');
        bugtracker_form = new Y.lazr.FormOverlay({
            headerContent: '<h2>Create Milestone</h2>',
            form_submit_button: form_submit_button,
            centered: true,
            form_submit_callback: save_new_bugtracker,
            visible: false
        });
        bugtracker_form.loadFormContentAndRender(
                '/bugs/bugtrackers/+newbugtracker/++form++');
        bugtracker_form.render();

        // The container needs to be 62 pixels narrower than the
        // boundingBox.
        bugtracker_form.get('boundingBox').setStyle('width', '580px');
        container = bugtracker_form.get('boundingBox').query(
            '.content_box_container');
        container.setStyle('width', '518px');

        bugtracker_form.show();
    };

    var show_bugtracker_form = function(e) {
        e.preventDefault();
        if (bugtracker_form) {
            bugtracker_form.show();
        } else {
            // This function call is asynchronous, so we can move
            // bugtracker_form.show() below it.
            setup_bugtracker_form();
        }
    };

    /**
      * Attaches a bugtracker form overlay widget to an element.
      *
      * @method attach_widget
      * @param {Object} config Object literal of config name/value pairs.
      *                        activate_node is the node that shows the form
      *                            when it is clicked.
      *                        next_step is the function to be called after
      *                            the bugtracker is created.
      */
    namespace.attach_widget = function(config) {
        Y.log('lp.bugs.bugtracker_overlay.attach_widget()');
        if (Y.UA.ie) {
            return;
        }
        if (config === undefined) {
            throw new Error(
                "Missing attach_widget config for bugtracker_overlay.");
        }
        if (config.activate_node === undefined ||
            config.next_step === undefined) {
            throw new Error(
                "attach_widget config for bugtracker_overlay has " +
                "undefined properties.");
        }
        next_step = config.next_step;
        Y.log('lp.bugs.bugtracker_overlay.attach_widget() setup onclick');
        config.activate_node.addClass('js-action');
        config.activate_node.on('click', show_bugtracker_form);
    };

}, "0.1", {"requires": [
    "dom", "node", "io-base", "lazr.anim", "lazr.formoverlay", "lp.calendar"
    ]});
