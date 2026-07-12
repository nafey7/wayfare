/**
 * Global Test Teardown
 *
 * This script runs once after all tests to clean up the test environment.
 * It ensures no test data is left behind and connections are properly closed.
 */

import { teardownTestDatabase, getTestDatabaseStats } from './database-cleanup.js';

async function globalTeardown() {
  console.log('🧹 Starting global test teardown...');

  try {
    // Get final database statistics
    console.log('📊 Getting final test database statistics...');
    const finalStats = await getTestDatabaseStats();
    console.log('Final database state:', JSON.stringify(finalStats, null, 2));

    // Clean up test database
    console.log('🗃️ Cleaning up test database...');
    await teardownTestDatabase();

    // Log completion
    console.log('✅ Global test teardown completed successfully');

    // Summary report
    console.log('\n📋 Test Environment Summary:');
    console.log(`   Database: ${finalStats.database}`);
    console.log(`   Total collections: ${Object.keys(finalStats.collections).length}`);
    console.log(`   Total documents: ${Object.values(finalStats.collections).reduce((sum, count) => sum + count, 0)}`);
    console.log('   All test data has been cleaned up');

  } catch (error) {
    console.error('❌ Global test teardown failed:', error);
    // Don't exit with error code in teardown to avoid masking test failures
  }
}

export default globalTeardown;