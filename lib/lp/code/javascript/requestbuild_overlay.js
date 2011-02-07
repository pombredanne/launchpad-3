/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * A form overlay that can request builds for a recipe..
 *
 * @namespace Y.lp.code.recipebuild_overlay
 * @requires  dom, node, io-base, lazr.anim, lazr.formoverlay
 */
YUI.add('lp.code.requestbuild_overlay', function(Y) {
Y.log('loading lp.code.requestbuild_overlay');

var namespace = Y.namespace('lp.code.requestbuild_overlay');

var lp_client;
var request_build_overlay;
var error_handler;

function set_up_lp_client() {
    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }
}

/*
 * Connect the links to the javascript events.
 */

namespace.connect_requestbuild = function(config) {

    error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = function() {
        destroy_temporary_spinner();
    };
    error_handler.showError = function(error_message) {
        destroy_temporary_spinner();
        alert('An unexpected error has occurred.');
        Y.log(error_message);
    };

    if (config === undefined) {
        throw new Error(
            "Missing connect_requestbuild config for requestbuild_overlay.");
    }


    request_build_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Request builds for ' + config.recipe_name + ' </h2>',
        form_submit_button: Y.Node.create(
            '<button type="submit" name="field.actions.request" ' +
            'value="Request builds" class="lazr-pos lazr-btn">Ok</button>'),
        form_cancel_button: Y.Node.create(
            '<button type="button" name="requestbuild.actions.cancel" ' +
            'class="lazr-neg lazr-btn">Cancel</button>'),
        centered: true,
        form_submit_callback: do_request_builds,
        visible: false
    });
    request_build_overlay.render();
    request_build_overlay.loadFormContentAndRender('+request-builds/++form++');
    var request_build_handle = Y.one('#request-builds');
    request_build_handle.addClass('js-action');
    request_build_handle.on('click', function(e) {
        e.preventDefault();
        request_build_overlay.show();
    });
};

function do_request_builds(data) {
    request_build_overlay.hide();
    create_temporary_spinner();

    var query_str = '';
    query_str = LP.client.append_qs(query_str, 'field.archive', data['field.archive']);
    query_str = LP.client.append_qs(query_str, 'field.distros', data['field.distros']);
    query_str = LP.client.append_qs(query_str, 'field.actions.request', 'Request builds');

    var uri = '+request-builds';
    var client = this;

    var y_config = {
                     method: "POST",
                     headers: {'Accept': 'application/json'},
            on: {
                success: function(id, response) {
                    alert("success: " + response.responseText);
                    destroy_temporary_spinner();
                },
                failure: error_handler.getFailureHandler()
            },
         arguments: [client, uri],
         data: query_str

    };
    var submit_url = LP.client.cache.context.self_link.replace('/api/devel', '');
    submit_url = submit_url+"/"+uri;
    Y.io(submit_url, y_config);
}

/*
 * Show the temporary "Requesting..." text
 */
function create_temporary_spinner() {
    var temp_spinner = Y.Node.create([
        '<div id="temp-spinner">',
        '<img src="/@@/spinner"/>Requesting...',
        '</div>'].join(''));
    var request_build_handle = Y.one('#request-builds');
    request_build_handle.insert(temp_spinner, request_build_handle);

}

/*
 * Destroy the temporary "Requesting..." text
 */
function destroy_temporary_spinner() {

    var temp_spinner = Y.one('#temp-spinner');
    var spinner_parent = temp_spinner.get('parentNode');
    spinner_parent.removeChild(temp_spinner);
}

}, "0.1", {"requires": [
    "dom", "node", "io-base", "lazr.anim", "lazr.formoverlay",
    "lp.app.calendar", "lp.client.plugins"
    ]});
