#!/usr/bin/env node

const newman = require('newman');
const fs = require('fs');
const path = require('path');

// Configuration
const config = {
    collection: './My_FirstCare_Opera_Panel_API.postman_collection.json',
    environment: './My_FirstCare_Opera_Panel.postman_environment.json',
    reporters: ['cli', 'json', 'html'],
    reporter: {
        html: {
            export: './test-results/newman-report.html'
        },
        json: {
            export: './test-results/newman-report.json'
        }
    },
    iterationCount: 1,
    delayRequest: 500, // 500ms delay between requests
    timeout: 30000, // 30 second timeout
    insecure: true, // Allow self-signed certificates
    color: 'on'
};

// Create test results directory
const testResultsDir = './test-results';
if (!fs.existsSync(testResultsDir)) {
    fs.mkdirSync(testResultsDir, { recursive: true });
}

console.log('🚀 Starting My FirstCare Opera Panel API Tests...\n');

// Function to run Newman tests
function runTests() {
    return new Promise((resolve, reject) => {
        newman.run(config, (err, summary) => {
            if (err) {
                console.error('❌ Newman run failed:', err);
                reject(err);
                return;
            }

            console.log('\n📊 Test Summary:');
            console.log('================');
            console.log(`Total Requests: ${summary.run.stats.requests.total}`);
            console.log(`Passed Requests: ${summary.run.stats.requests.total - summary.run.stats.requests.failed}`);
            console.log(`Failed Requests: ${summary.run.stats.requests.failed}`);
            console.log(`Total Assertions: ${summary.run.stats.assertions.total}`);
            console.log(`Passed Assertions: ${summary.run.stats.assertions.total - summary.run.stats.assertions.failed}`);
            console.log(`Failed Assertions: ${summary.run.stats.assertions.failed}`);
            console.log(`Average Response Time: ${summary.run.timings.responseAverage}ms`);
            console.log(`Total Test Duration: ${summary.run.timings.completed - summary.run.timings.started}ms`);

            // Log failed tests
            if (summary.run.failures.length > 0) {
                console.log('\n❌ Failed Tests:');
                console.log('================');
                summary.run.failures.forEach((failure, index) => {
                    console.log(`${index + 1}. ${failure.error.name}: ${failure.error.message}`);
                    console.log(`   Request: ${failure.source.name}`);
                    console.log(`   Test: ${failure.error.test}\n`);
                });
            }

            // Generate summary report
            const summaryReport = {
                timestamp: new Date().toISOString(),
                status: summary.run.stats.assertions.failed === 0 ? 'PASSED' : 'FAILED',
                stats: {
                    requests: summary.run.stats.requests,
                    assertions: summary.run.stats.assertions,
                    timings: summary.run.timings
                },
                failures: summary.run.failures.map(failure => ({
                    test: failure.error.test,
                    message: failure.error.message,
                    request: failure.source.name
                }))
            };

            // Save summary report
            fs.writeFileSync(
                path.join(testResultsDir, 'test-summary.json'),
                JSON.stringify(summaryReport, null, 2)
            );

            console.log(`\n📁 Reports saved to: ${testResultsDir}/`);
            console.log('   - newman-report.html (HTML report)');
            console.log('   - newman-report.json (JSON report)');
            console.log('   - test-summary.json (Summary report)');

            if (summary.run.stats.assertions.failed === 0) {
                console.log('\n✅ All tests passed! API is healthy.');
                resolve(summaryReport);
            } else {
                console.log('\n❌ Some tests failed. Check the reports for details.');
                reject(new Error(`${summary.run.stats.assertions.failed} assertions failed`));
            }
        });
    });
}

// Health check function
async function healthCheck() {
    console.log('🔍 Performing health check...');
    
    const healthConfig = {
        collection: {
            info: {
                name: 'Health Check',
                schema: 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
            },
            item: [
                {
                    name: 'Health Check',
                    request: {
                        method: 'GET',
                        header: [],
                        url: {
                            raw: '{{base_url}}/health',
                            host: ['{{base_url}}'],
                            path: ['health']
                        }
                    },
                    event: [
                        {
                            listen: 'test',
                            script: {
                                exec: [
                                    'pm.test("Health check successful", function () {',
                                    '    pm.response.to.have.status(200);',
                                    '});',
                                    '',
                                    'pm.test("Response has status field", function () {',
                                    '    const response = pm.response.json();',
                                    '    pm.expect(response).to.have.property("status");',
                                    '});'
                                ]
                            }
                        }
                    ]
                }
            ]
        },
        environment: config.environment,
        reporters: ['cli']
    };

    return new Promise((resolve, reject) => {
        newman.run(healthConfig, (err, summary) => {
            if (err || summary.run.stats.assertions.failed > 0) {
                console.log('❌ Health check failed - API may be down');
                reject(err || new Error('Health check failed'));
            } else {
                console.log('✅ Health check passed - API is running');
                resolve();
            }
        });
    });
}

// Main execution
async function main() {
    try {
        // Check if collection and environment files exist
        if (!fs.existsSync(config.collection)) {
            throw new Error(`Collection file not found: ${config.collection}`);
        }
        if (!fs.existsSync(config.environment)) {
            throw new Error(`Environment file not found: ${config.environment}`);
        }

        // Perform health check first
        await healthCheck();

        // Run the full test suite
        await runTests();

        console.log('\n🎉 Test execution completed successfully!');
        process.exit(0);

    } catch (error) {
        console.error('\n💥 Test execution failed:', error.message);
        process.exit(1);
    }
}

// Handle command line arguments
if (process.argv.includes('--health-only')) {
    healthCheck()
        .then(() => {
            console.log('✅ Health check completed');
            process.exit(0);
        })
        .catch((error) => {
            console.error('❌ Health check failed:', error.message);
            process.exit(1);
        });
} else {
    main();
} 