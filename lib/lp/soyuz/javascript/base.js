/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Auxiliary functions used in Soyuz pages
 *
 * @module soyuz
 * @submodule base
 * @namespace soyuz
 * @requires yahoo, node
 */

YUI.add('lp.soyuz.base', function(Y) {

var namespace = Y.namespace('lp.soyuz.base');


/*
 * Return a node containing a standard failure message to be used
 * in XHR-based page updates.
 */
namespace.makeFailureNode = function (text, handler) {
    var failure_message = Y.Node.create('<p>');
    failure_message.addClass('update-failure-message');

    var message = Y.Node.create('<span>');
    message.set('innerHTML', text);
    failure_message.appendChild(message);

    var retry_link = Y.Node.create('<a>');
    retry_link.addClass('update-retry');
    retry_link.set('href', '');
    retry_link.set('innerHTML', 'Retry');
    retry_link.on('click', handler);
    failure_message.appendChild(retry_link);

    return failure_message;
};


/*
 * Return a node containing a standard in-progress message to be used
 * in XHR-based page updates.
 */
namespace.makeInProgressNode = function (text) {
    var in_progress_message = Y.Node.create('<p>');
    var message = Y.Node.create('<span>');

    message.set('innerHTML', text);
    in_progress_message.addClass('update-in-progress-message');
    in_progress_message.appendChild(message);

    return in_progress_message;
};

}, "0.1", {"requires":["node"]});
