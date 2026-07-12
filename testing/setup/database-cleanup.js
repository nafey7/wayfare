/**
 * Database Cleanup Utilities for Playwright Tests
 *
 * This module provides functions to clean test data and manage database state
 * between test runs. It ensures test isolation and prevents data pollution.
 */

import { MongoClient } from 'mongodb';

// Test database configuration
const TEST_DB_CONFIG = {
  uri: process.env.MONGODB_URI || 'mongodb://localhost:27018',
  dbName: process.env.DATABASE_NAME || 'voya_test',
  options: {
    maxPoolSize: 5,
    serverSelectionTimeoutMS: 5000,
    socketTimeoutMS: 45000,
  }
};

let testDbClient = null;
let testDb = null;

/**
 * Connect to the test database
 */
export async function connectToTestDatabase() {
  if (testDbClient && testDb) {
    return { client: testDbClient, db: testDb };
  }

  try {
    console.log(`🔌 Connecting to test database: ${TEST_DB_CONFIG.dbName}`);
    testDbClient = new MongoClient(TEST_DB_CONFIG.uri, TEST_DB_CONFIG.options);
    await testDbClient.connect();
    testDb = testDbClient.db(TEST_DB_CONFIG.dbName);

    console.log('✅ Connected to test database successfully');
    return { client: testDbClient, db: testDb };
  } catch (error) {
    console.error('❌ Failed to connect to test database:', error);
    throw error;
  }
}

/**
 * Disconnect from the test database
 */
export async function disconnectFromTestDatabase() {
  if (testDbClient) {
    try {
      await testDbClient.close();
      testDbClient = null;
      testDb = null;
      console.log('🔌 Disconnected from test database');
    } catch (error) {
      console.error('❌ Error disconnecting from test database:', error);
    }
  }
}

/**
 * Clean all test data from the database
 * This is the main cleanup function used between test runs
 */
export async function cleanupAllTestData() {
  const { db } = await connectToTestDatabase();

  console.log('🧹 Starting comprehensive test data cleanup...');

  try {
    const cleanupResults = {};

    // Clean users (keep any admin users)
    const userDeleteResult = await db.collection('users').deleteMany({
      $or: [
        { email: { $regex: /test.*@example\.com/i } },
        { email: { $regex: /.*-test@.*/i } },
        { email: { $regex: /.*\+test@.*/i } },
        { email: { $regex: /email-test@.*/i } }
      ]
    });
    cleanupResults.users = userDeleteResult.deletedCount;

    // Clean chats
    const chatDeleteResult = await db.collection('chats').deleteMany({});
    cleanupResults.chats = chatDeleteResult.deletedCount;

    // Clean chat history
    const historyDeleteResult = await db.collection('chat_history').deleteMany({});
    cleanupResults.chatHistory = historyDeleteResult.deletedCount;

    // Clean trips
    const tripDeleteResult = await db.collection('trips').deleteMany({});
    cleanupResults.trips = tripDeleteResult.deletedCount;

    // Clean sessions
    const sessionDeleteResult = await db.collection('sessions').deleteMany({});
    cleanupResults.sessions = sessionDeleteResult.deletedCount;

    // Reset counters to base values
    await db.collection('counters').updateOne(
      { _id: 'user_id' },
      { $set: { sequence_value: 1000 } }
    );
    await db.collection('counters').updateOne(
      { _id: 'chat_id' },
      { $set: { sequence_value: 1000 } }
    );
    await db.collection('counters').updateOne(
      { _id: 'trip_id' },
      { $set: { sequence_value: 1000 } }
    );

    console.log('✅ Test data cleanup completed:', cleanupResults);
    return cleanupResults;

  } catch (error) {
    console.error('❌ Error during test data cleanup:', error);
    throw error;
  }
}

/**
 * Clean specific user data by email pattern
 */
export async function cleanupUserData(emailPattern) {
  const { db } = await connectToTestDatabase();

  console.log(`🧹 Cleaning user data for pattern: ${emailPattern}`);

  try {
    const userDeleteResult = await db.collection('users').deleteMany({
      email: { $regex: emailPattern, $options: 'i' }
    });

    console.log(`✅ Deleted ${userDeleteResult.deletedCount} users matching pattern`);
    return userDeleteResult.deletedCount;

  } catch (error) {
    console.error('❌ Error during user data cleanup:', error);
    throw error;
  }
}

/**
 * Create a test user for testing purposes
 */
export async function createTestUser(email, userData = {}) {
  const { db } = await connectToTestDatabase();

  const defaultUserData = {
    email: email,
    first_name: userData.firstName || 'Test',
    last_name: userData.lastName || 'User',
    is_verified: userData.isVerified || false,
    is_active: userData.isActive !== false, // Default to true
    created_at: new Date(),
    updated_at: new Date(),
    profile: {
      preferences: {},
      settings: {},
      ...userData.profile
    }
  };

  try {
    const result = await db.collection('users').insertOne(defaultUserData);
    console.log(`✅ Created test user: ${email} with ID: ${result.insertedId}`);

    return {
      userId: result.insertedId,
      email: email,
      ...defaultUserData
    };

  } catch (error) {
    if (error.code === 11000) { // Duplicate key error
      console.log(`⚠️ Test user ${email} already exists`);
      const existingUser = await db.collection('users').findOne({ email });
      return {
        userId: existingUser._id,
        email: email,
        ...existingUser
      };
    }
    console.error('❌ Error creating test user:', error);
    throw error;
  }
}

/**
 * Get database statistics for debugging
 */
export async function getTestDatabaseStats() {
  const { db } = await connectToTestDatabase();

  const collections = ['users', 'chats', 'chat_history', 'trips', 'sessions', 'counters'];
  const stats = {
    database: TEST_DB_CONFIG.dbName,
    collections: {},
    timestamp: new Date()
  };

  for (const collectionName of collections) {
    try {
      stats.collections[collectionName] = await db.collection(collectionName).countDocuments();
    } catch (error) {
      stats.collections[collectionName] = 0;
    }
  }

  return stats;
}

/**
 * Verify test database is ready and accessible
 */
export async function verifyTestDatabase() {
  try {
    const { db } = await connectToTestDatabase();

    // Try to ping the database
    await db.admin().ping();

    // Get basic stats
    const stats = await getTestDatabaseStats();

    console.log('✅ Test database verification successful');
    console.log('📊 Database stats:', JSON.stringify(stats, null, 2));

    return true;
  } catch (error) {
    console.error('❌ Test database verification failed:', error);
    return false;
  }
}

/**
 * Setup function for test suites
 * Call this in beforeAll() hooks
 */
export async function setupTestDatabase() {
  console.log('🚀 Setting up test database...');

  const isReady = await verifyTestDatabase();
  if (!isReady) {
    throw new Error('Test database is not ready');
  }

  await cleanupAllTestData();
  console.log('✅ Test database setup complete');
}

/**
 * Teardown function for test suites
 * Call this in afterAll() hooks
 */
export async function teardownTestDatabase() {
  console.log('🧹 Tearing down test database...');

  await cleanupAllTestData();
  await disconnectFromTestDatabase();

  console.log('✅ Test database teardown complete');
}

// Export configuration for external use
export const testDbConfig = TEST_DB_CONFIG;