/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * A form overlay that can request builds for a recipe..
 *
 * @namespace Y.lp.code.recipebuild_overlay
 * @requires  dom, node, io-base, lazr.anim, lazr.formoverlay
 */
YUI.add('lp.code.requestbuild_overlay', function(Y) {

var namespace = Y.namespace('lp.code.requestbuild_overlay');

var lp_client;
var request_build_overlay = null;
var request_build_response_handler;
var request_daily_build_response_handler;

function set_up_lp_client() {
    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }
}

// This handler is used to process the results of form submission or other
// such operation (eg get, post). It provides some boiler plate and allows the
// developer to specify onSuccess and onError hooks. It is quite generic and
// perhaps could be moved to an infrastructure class.

RequestResponseHandler = function () {};
RequestResponseHandler.prototype = {
    clearProgressUI: function () {},
    showError: function (error_msg) {},
    getErrorHandler: function (errorCallback) {
        var self = this;
        return function (id, response) {
            self.clearProgressUI();
            // If it was a timeout...
            if (response.status == 503) {
                self.showError(
                    'Timeout error, please try again in a few minutes.');
            } else {
                if (errorCallback != null) {
                    errorCallback(self, id, response);
                } else {
                    self.showError(response.responseText);
                }
            }
        };
    },
    getSuccessHandler: function (successCallback) {
        var self = this;
        return function (id, response) {
            self.clearProgressUI();
            successCallback(self, id, response);
        };
    }
};

namespace.connect_requestbuilds = function() {

    var request_build_handle = Y.one('#request-builds');
    request_build_handle.addClass('js-action');
    request_build_handle.on('click', function(e) {
        e.preventDefault();
        if (request_build_overlay == null) {
            // Render the form and load the widgets to display
            var recipe_name = LP.client.cache.context['name'];
            request_build_overlay = new Y.lazr.FormOverlay({
                headerContent: '<h2>Request builds for '
                                    + recipe_name + ' </h2>',
                form_submit_button: Y.Node.create(
                    '<button type="submit" name="field.actions.request" ' +
                    'value="Request builds">Request Builds</button>'),
                form_cancel_button: Y.Node.create(
                    '<button type="button" name="field.actions.cancel" ' +
                    '>Cancel</button>'),
                centered: true,
                form_submit_callback: do_request_builds,
                visible: false
            });
            request_build_overlay.render();
        }
        request_build_overlay.clearError();
        var loading_spinner = [
            '<div id="temp-spinner">',
            '<img src="/@@/spinner"/>Loading...',
            '</div>'].join('');
        request_build_overlay.form_node.set("innerHTML", loading_spinner);
        request_build_overlay.loadFormContentAndRender('+builds/++form++');
        request_build_overlay.show();
    });

    // Wire up the processing hooks
    request_build_response_handler = new RequestResponseHandler();
    request_build_response_handler.clearProgressUI = function() {
        destroy_temporary_spinner();
    };
    request_build_response_handler.showError = function(error) {
        request_build_overlay.showError(error);
        Y.log(error);
    };
};

namespace.connect_requestdailybuild = function() {

    var request_daily_build_handle = Y.one('#request-daily-build');
    request_daily_build_handle.on('click', function(e) {
        e.preventDefault();

        create_temporary_spinner(
                "Requesting build...", request_daily_build_handle);
        request_daily_build_handle.addClass("unseen");

        var base_url = LP.client.cache.context.web_link;
        var submit_url = base_url+"/+request-daily-build";
        var current_builds = harvest_current_build_records();

        var qs = LP.client.append_qs('', 'field.actions.build', 'Build now');
        var y_config = {
            method: "POST",
            headers: {'Accept': 'application/xhtml'},
            on: {
                failure: request_daily_build_response_handler.getErrorHandler(
                    function(handler, id, response) {
                        request_daily_build_handle.removeClass("unseen");
                        var server_error = 'Server error, ' +
                                           'please contact an administrator.';
                        handler.showError(server_error);
                    }),
                success:
                    request_daily_build_response_handler.getSuccessHandler(
                    function(handler, id, response) {
                        display_build_records(
                                response.responseText, current_builds)
                    }
                  )
            },
            data: qs
        };
        Y.io(submit_url, y_config);
    });

    // Wire up the processing hooks
    request_daily_build_response_handler = new RequestResponseHandler();
    request_daily_build_response_handler.clearProgressUI = function() {
        destroy_temporary_spinner();
    };
    request_daily_build_response_handler.showError = function(error) {
        alert(error);
        Y.log(error);
    };
};

/*
 * A function to return the current build records as displayed on the page
 */
function harvest_current_build_records() {
    var row_classes = ['package-build', 'binary-build'];
    var builds = new Array();
    Y.Array.each(row_classes, function(row_class) {
        Y.all('.'+row_class).each(function(row) {
            var row_id = row.getAttribute('id');
            if (builds.indexOf(row_id)<0) {
                builds.push(row_id);
            }
        });
    });
    return builds;
}

/*
 * Render build records and flash the new ones
 */
function display_build_records(build_records_markup, current_builds) {
    var target = Y.one('#builds-target');
    target.set('innerHTML', build_records_markup);
    var new_builds = harvest_current_build_records();
    Y.Array.each(new_builds, function(row_id) {
        if( current_builds.indexOf(row_id)>=0 )
            return;
        var row = Y.one('#'+row_id);
        var anim = Y.lazr.anim.green_flash({node: row});
        anim.run();
    });
}

/*
 * Perform any client side validation
 * Return: true if data is valid
 */
function validate(data) {
    var distros = data['field.distros']
    if (Y.Object.size(distros) == 0) {
        request_build_response_handler.showError(
                "You need to specify at least one distro series for " +
                "which to build.");
        return false;
    }
    return true;
}

/*
 * The form submit function
 */
function do_request_builds(data) {
    if (!validate(data))
        return;
    var spinner_location = Y.one('.yui3-lazr-formoverlay-actions');
    create_temporary_spinner("Requesting builds...", spinner_location);

    var base_url = LP.client.cache.context.web_link;
    var submit_url = base_url+"/+builds";
    var current_builds = harvest_current_build_records();
    var y_config = {
        method: "POST",
        headers: {'Accept': 'application/json; application/xhtml'},
        on: {
            failure: request_build_response_handler.getErrorHandler(
                function(handler, id, response) {
                    if( response.status >= 500 ) {
                        // There's some error content we need to display.
                        request_build_overlay.set(
                                'form_content', response.responseText);
                        request_build_overlay.get("form_submit_button")
                                .addClass('unseen');
                        request_build_overlay.renderUI();
                        //We want to force the form to be re-created
                        request_build_overlay = null;
                        return;
                    }
                    var error_info = Y.JSON.parse(response.responseText)
                    var errors = [];
                    for (var field_name in error_info)
                        errors.push(error_info[field_name]);
                    handler.showError(errors);
                }),
            success: request_build_response_handler.getSuccessHandler(
                function(handler, id, response) {
                    request_build_overlay.hide();
                    display_build_records(
                            response.responseText, current_builds)
                })
        },
        form: {
            id: request_build_overlay.form_node,
            useDisabled: true
        }
    };
    Y.io(submit_url, y_config);
}

/*
 * Show the temporary "Requesting..." text
 */
function create_temporary_spinner(text, node) {
    // Add the temp "Requesting build..." text
    var temp_spinner = Y.Node.create([
        '<div id="temp-spinner">',
        '<img src="/@@/spinner"/>',
        text,
        '</div>'].join(''));
    node.insert(temp_spinner, node);
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
    "dom", "node", "io-base", "lazr.anim", "lazr.formoverlay"
    ]});
