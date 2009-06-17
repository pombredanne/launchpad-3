/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * A milestone form overlay that can create a milestone within any page.
 *
 * @module Y.lp.milestoneoverlay
 * @requires  dom, node, io-base, lazr.anim, lazr.formoverlay
 */
YUI.add('lp.milestoneoverlay', function(Y) {
    Y.log('loading lp.milestoneoverlay');
    var milestoneoverlay = Y.namespace('lp.milestoneoverlay');

    var milestone_form;
    var milestone_form_uri;
    var series_uri;
    var next_step;

    var error_box_html =
        '<p id="milestone-error" class="error message" ' +
        'style="width: 80%; display:none;' +
               'left: 0; right: 0; ' +
               'margin-left: auto; margin-right: auto; ' +
               'margin-top: 2em; margin-bottom: 2em;" />';

    var error_box_html =
        '<div style="margin: 2em">' +
        '<p id="milestone-error" class="error message" ' +
        'style="width: 80%; display:none; ' +
                'padding-left: 1.5em; padding-right: 1.5em;" />' +
        '</div>';

    var create_form_overlay = function (id, response, args) {
        var form_content = error_box_html + response.responseText;
        var form_submit_button = Y.Node.create(
            '<input type="submit" name="field.actions.register" ' +
            'id="formoverlay-add-milestone" value="Create Milestone"/>');
        milestone_form = new Y.lazr.FormOverlay({
            headerContent: '<h2>Create Milestone</h2>',
            form_content: form_content,
            form_submit_button: form_submit_button,
            centered: true,
            form_submit_callback: save_new_milestone,
            visible: false
        });
        milestone_form.render();
        milestone_form.show();
    };

    var save_new_milestone = function(data) {

        var parameters = {
            name: data['field.name'][0].toLowerCase(),
            code_name: data['field.code_name'][0],
            summary: data['field.summary'][0]
        };

        var date_targeted = Y.Lang.trim(data['field.dateexpected'][0]);
        if (date_targeted != '') {
            parameters.date_targeted = date_targeted;
        }

        var finish_new_milestone = function(ignore) {
            var error_box = Y.get('#milestone-error');
            error_box.set('innerHTML', '');
            error_box.setStyle('display', 'none');
            milestone_form.hide();
            // Reset the HTML form inside the widget.
            milestone_form.get('contentBox').query('form').reset();
            next_step(parameters);
        };

        client = new LP.client.Launchpad();
        client.named_post(series_uri, 'newMilestone', {
            parameters: parameters,
            on: {
                success: finish_new_milestone,
                failure: function (ignore, response, args) {
                    var error_box = Y.get('#milestone-error');
                    var error_message = '<strong>' + response.statusText +
                                        '</strong><p>' +
                                        response.responseText +
                                        '</p>';
                    error_box.set('innerHTML', error_message);
                    error_box.setStyle('display', 'block');
                }
            }
        });
    };


    var setup_milestone_form = function () {
        Y.io(milestone_form_uri, {
            on: {
                success: create_form_overlay,
                failure: function (ignore, response, args) {
                    var error_page = Y.Node.create('<div/>');
                    error_page.setStyle('position', 'absolute');
                    error_page.setStyle('top', '0');
                    error_page.setStyle('bottom', '0');
                    error_page.setStyle('left', '0');
                    error_page.setStyle('right', '0');
                    error_page.setStyle('margin', 'auto');
                    error_page.setStyle('width', '80%');
                    error_page.setStyle('height', '80%');
                    error_page.setStyle('overflow', 'auto');
                    error_page.setStyle('background', 'white');
                    error_page.setStyle('padding', '1em');
                    error_page.setStyle('border', '3px solid black');
                    var error_message = '<strong>' + response.statusText +
                                        '</strong><p>' +
                                        response.responseText +
                                        '</p>';
                    error_page.set('innerHTML', error_message);
                    var body = Y.get('body');
                    body.appendChild(error_page);
                }
            }
        });
    };

    show_milestone_form = function(e) {
        if (milestone_form) {
            milestone_form.show();
        } else {
            // This function call is asynchronous, so we can move
            // milestone_form.show() below it.
            setup_milestone_form();
        }
        e.preventDefault();
    };

    /**
      * Attaches a milestone form overlay widget to an element.
      *
      * @method attach_widget
      * @param {Object} config Object literal of config name/value pairs.
      *                        config.milestone_form_uri is the URI of the
      *                            milestone form to display.
      *                        config.series_uri is the URI to post the
      *                            form data to create the milestone.
      *                        activate_node is the node that shows the form
      *                            when it is clicked.
      *                        next_step is the function to be called after
      *                            the milestone is created.
      *                        success_callback is the function that is called
      *                            after the milestone is created. The form
      *                            parameters are passed as an argument.
      */
    milestoneoverlay.attach_widget = function(config) {
        if (Y.UA.ie) {
            return;
        }
        milestone_form_uri = config.milestone_form_uri;
        series_uri = config.series_uri;
        next_step = config.next_step;
        config.activate_node.on('click', show_milestone_form);
    }

}, '0.1', {
requires: [
    'dom', 'node', 'io-base', 'lazr.anim', 'lazr.formoverlay'
    ]});
