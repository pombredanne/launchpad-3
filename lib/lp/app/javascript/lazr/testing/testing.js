/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI.add("lazr.testing.runner", function(Y) {

/**
 * Testing utilities.
 *
 * @module lazr.testing
 * @namespace lazr
 */

Runner = Y.namespace("lazr.testing.Runner");

Runner.add = function(suite) {
    if ((typeof jstestdriver === "undefined")) {
        // If we are not running under JsTestDriver, then
        // register the suite with Y.Test.Runner and run it.
        Y.Test.Runner.add(suite);
    } else {
        // If ``jstestdriver`` is defined, that means we are
        // running under JsTestDriver, so instead register each
        // test case from the suite as a separate TestCase() with
        // JsTestDriver.
        var tests = [];

        Y.each(suite.items, function(testCase, idx) {
            var suiteName = suite.name;
            var testCaseName = testCase.name;

            var clone = {};
            for (var prop in testCase){
                // Clone everything that is not a test method.
                if (prop.indexOf("test") === -1){
                    clone[prop] = testCase[prop];
                }
            }

            // Now for each test method, create a JsTestDriver
            // TestCase that wraps a single YUI TestSuite, that wraps
            // a clone of the original TestCase but with only the
            // single test method that we are interested in.
            Y.each(testCase, function(property, name) {
                if (name.indexOf("test") === 0 &&
                    Y.Lang.isFunction(property)){
                    tests.push({"suiteName": suiteName,
                                "caseName": testCaseName,
                                "case": clone,
                                "methodName": name,
                                "method": property});
                }
            });
        });

        Y.each(tests, function(testObject, i) {
            testObject = tests[i];

            var fakeTestCase = {
                "setUp": Y.bind(function(testObject){
                    var testSuite = new Y.Test.Suite(testObject.suiteName);
                    var testCase = new Y.Test.Case(testObject['case']);
                    testCase[testObject.methodName] = testObject.method;
                    testSuite.add(testCase);
                    Y.Test.Runner.clear();
                    Y.Test.Runner.add(testSuite);
                }, this, testObject),
                "tearDown": function(){
                    Y.Test.Runner.clear();
                }
            };

            fakeTestCase[testObject.methodName] = Y.bind(function (testObject) {
                var results = [];

                var onComplete = function (methodName, results, e) {
                    Y.Test.Runner.unsubscribe("testcasecomplete");
                    results.push(e.results[methodName]);
                };

                Y.Test.Runner.subscribe(
                    "testcasecomplete",
                    Y.bind(onComplete, this, testObject.methodName, results),
                    Y.Test.Runner);

                Clock.reset();
                Y.Test.Runner.run();
                var i = 100;
                while (i--) {
                    if (!Y.Test.Runner.isRunning()){
                        break;
                    }
                    Clock.tick(100);
                }

                var result = results.pop();
                if (result === undefined) {
                    fail("Test did not finish after 100 iterations.");
                } else {
                    if (result.result == "fail") {
                        fail(result.message);
                    }
                }

            }, this, testObject);

            // JSLint will complain if the constructur is used without `new`
            // and if the result of `new` is not used. The TestCase class is
            // defined globally by jstestdriver and automatically registers
            // itself, so it is not necessary to return this object.
            var ignored = new TestCase(
                testObject.caseName + "." + testObject.methodName,
                fakeTestCase);
        });
    }
};

Runner.run = function(suite) {
    Y.on("domready", function() {
        if ((typeof jstestdriver === "undefined")) {
            // If we are not running under JsTestDriver, then run all
            // the registered test suites with Y.Test.Runner.
            var yconsole = new Y.Console({
                newestOnTop: false,
                useBrowserConsole: true
            });
            yconsole.render("#log");
            Y.Test.Runner.run();
        }
    });
};

}, "0.1", {"requires": ["oop", "test", "console"]});
