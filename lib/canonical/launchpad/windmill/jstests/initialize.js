/* 
Copyright 2009 Canonical Ltd.  This software is licensed under the
GNU Affero General Public License version 3 (see the file LICENSE).

Contains the JS fixtures we use to test AJAX call in windmill.

Since AJAX calls will complete asynchronously, we need to use a 
synchronisation mechanism.
 
 */


/* A synchronized test.
 * @param name The name of the test, the DOM node used for synchronization
 *      will use that name.
 *
 * @param body This is a list of functions or strings or windmill action
 *      object. That makes this test body.
 *      
 * @param debug (Optional) If this is set to true, tracing information 
 *      will be logged on the Firebug console.
 */
function SynchronizedTest(name, body, debug) {
    this.name = name;
    this.debug = !!debug;
    this.synced = false;

    /* Create the test body. */
    this.test_body = [];
    this.add_windmill_actions(this.test_body, body);

    /*
     * The tear down is also as an array, so that many cleanup
     * actions can be tacked to it using add_cleanups()
     */
    // Windmill doesn't like empty array teardown. So we define it as an
    // empty object, which gets replaced by an array when add_cleanups is
    // called.
    //this.teardown = [];
    this.teardown = function () {};
}


/* The YUI instance used by SynchronizedTest. */
SynchronizedTest.prototype.Y = YUI({
    bootstrap: false,
    fetchCSS: false,
    combine: false,
    timeout: 50
    }).use('dump');

/* Create the synchronization node, that should make the wait() caller
 * return.
 *
 * @param result This object will be available from the result attribute.
 *      This can be used to provide information passed to the callback 
 *      and that we want to make assertion on.
 */
SynchronizedTest.prototype.sync = function (result) {
    this.log('sync() called with ' + this.Y.dump(result));
    this.result = result;
    this.synced = true;
};


/* Convert a sequence of test items and adds them to a windmill array 
 * test specification.
 *
 * That method is used by the constructor and add_cleanups method.
 */
SynchronizedTest.prototype.add_windmill_actions = function (list, items) {
    var test = this;

    /* Windmill invokes all test functions without setting the this parameter.
     * So we create wrapper that will pass it to our functions.
     */
    function create_test_wrapper (func) {
        return function () { func(test); };
    }

    for (var i=0; i< items.length; i++) {
        var test_item = items[i];
        var yui_lang = this.Y.Lang;
        if (yui_lang.isFunction(test_item)) {
            //Create a wrapper that passes the test as first parameter.
            list.push(create_test_wrapper(test_item));
        } else if (yui_lang.isString(test_item)) {
            //This calls a method on the test. And sticks the result
            //in the test body. Common use case is to use 'wait_action' to
            //add a windmill wait action for the synchronizing condition.
            var action = test[test_item].call(test);
            list.push(action);
        } else if (yui_lang.isObject(test_item)) {
            //We expect this to be a Windmill action.
            list.push(test_item);
        } else {
            throw new Error(
                'Unknown test predicate: ' + this.Y.dump(test_item));
        }
    }
};

/* Add functions/actions to the "teardown" test.
 *
 * @param cleanups An array of functions, or strings or objects representing
 *      windmill actions. (Like in the test body parameter.)
 */
SynchronizedTest.prototype.add_cleanups = function (cleanups) {
    if (this.Y.Lang.isFunction(this.teardown)) {
        this.teardown = [];
    }
    this.add_windmill_actions(this.teardown, cleanups);
};

/* Return a windmill action that can be used to wait for 
 * the synchronization to happen.
 */
SynchronizedTest.prototype.wait_action = function () {
    var test = this;
    return {
        method: "waits.forJS",
        params: {
            //The function waits for the synced attribute to be set to true;
            //and then resets it so that next synchronization action work.
            js: function () {
                if (test.synced) {
                    test.synced = false;
                    return true;
                } else {
                    return false;
                }
            },
            timeout: 8000
        }
    };
};


/* Output a log message when debug is turned on.
 */
SynchronizedTest.prototype.log = function (message) {
    if (this.debug && console) {
        console.log(this.name + ': ' + message);
    }
};


/* Return a configuration object that can be used as a on
 * specification to YUI.io.
 *
 * It basically will call the test sync method, and save the
 * name of the handler called, and the arguments list.
 */
SynchronizedTest.prototype.create_yui_sync_on = function () {
    var test = this;
    return {
        success: function () {
            test.sync({callback: 'success', args: test.Y.Array(arguments)});
        },
        failure: function () {
            test.sync({callback: 'failure', args: test.Y.Array(arguments)});
        }
    };
};
