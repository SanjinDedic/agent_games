import React from 'react';

/**
 * Per-test-case results panel for tutorial exercises: a pass/fail summary
 * banner, one row per test case (call, expected vs actual, error), and any
 * captured print output.
 */
function ExerciseResults({ data }) {
    if (!data) return null;

    const tests = data.test_results || [];
    const passedCount = tests.filter((t) => t.passed).length;
    const allPassed = tests.length > 0 && passedCount === tests.length;

    return (
        <div className="space-y-4">
            {/* Summary banner */}
            <div
                className={`rounded-lg p-4 font-medium text-white ${
                    allPassed ? "bg-success" : "bg-notice-orange"
                }`}
            >
                {allPassed
                    ? `🎉 All ${tests.length} tests passed — exercise complete!`
                    : `${passedCount} of ${tests.length} tests passed`}
            </div>

            {/* Per-test results */}
            <ul className="space-y-2">
                {tests.map((test, idx) => (
                    <li
                        key={idx}
                        className={`rounded-lg border p-3 ${
                            test.passed
                                ? "border-success/40 bg-success/5"
                                : "border-danger/40 bg-danger/5"
                        }`}
                    >
                        <div className="flex items-center gap-2 font-medium text-ui-dark">
                            <span>{test.passed ? "✅" : "❌"}</span>
                            <span>{test.name}</span>
                        </div>
                        <div className="mt-1 ml-7 font-mono text-sm text-ui-dark/80">
                            <div>{test.call}</div>
                            {!test.passed && (
                                <div className="mt-1">
                                    {test.error ? (
                                        <span className="text-danger">{test.error}</span>
                                    ) : (
                                        <>
                                            <div>
                                                expected:{" "}
                                                <span className="text-success">
                                                    {JSON.stringify(test.expected)}
                                                </span>
                                            </div>
                                            <div>
                                                got:{" "}
                                                <span className="text-danger">
                                                    {test.actual ?? "nothing"}
                                                </span>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    </li>
                ))}
            </ul>

            {/* Captured print output */}
            {data.stdout && (
                <div>
                    <h3 className="font-medium text-ui-dark mb-1">Print output</h3>
                    <pre className="bg-[#1e1e1e] text-gray-100 rounded-lg p-3 text-sm overflow-x-auto">
                        {data.stdout}
                    </pre>
                </div>
            )}
        </div>
    );
}

export default ExerciseResults;
