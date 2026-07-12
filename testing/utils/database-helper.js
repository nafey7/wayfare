/**
 * Database Helper for Playwright Tests
 *
 * Provides MongoDB operations within Playwright tests without bash/mongosh.
 * Uses the same connection logic as global setup/teardown for consistency.
 */

import { MongoClient } from 'mongodb';

// Test database configuration (matches database-cleanup.js)
const TEST_DB_CONFIG = {
  uri: process.env.MONGODB_URI || 'mongodb://localhost:27018',
  dbName: process.env.DATABASE_NAME || 'voya_test',
  options: {
    maxPoolSize: 5,
    serverSelectionTimeoutMS: 5000,
    socketTimeoutMS: 45000,
  }
};

/**
 * DatabaseHelper class for test database operations
 *
 * Example usage in tests:
 * ```js
 * const dbHelper = new DatabaseHelper();
 * await dbHelper.connect();
 * await dbHelper.clearTestUsers();
 * const user = await dbHelper.getUser('test@example.com');
 * await dbHelper.disconnect();
 * ```
 */
export class DatabaseHelper {
  constructor() {
    this.client = null;
    this.db = null;
  }

  /**
   * Connect to test database
   */
  async connect() {
    if (this.client && this.db) {
      return; // Already connected
    }

    try {
      this.client = new MongoClient(TEST_DB_CONFIG.uri, TEST_DB_CONFIG.options);
      await this.client.connect();
      this.db = this.client.db(TEST_DB_CONFIG.dbName);
    } catch (error) {
      console.error('❌ Failed to connect to test database:', error);
      throw error;
    }
  }

  /**
   * Disconnect from test database
   */
  async disconnect() {
    if (this.client) {
      try {
        await this.client.close();
        this.client = null;
        this.db = null;
      } catch (error) {
        console.error('❌ Error disconnecting from test database:', error);
      }
    }
  }

  // ===========================================================================
  // CLEANUP OPERATIONS
  // ===========================================================================

  /**
   * Clear all test users (safe - only deletes test patterns)
   */
  async clearTestUsers() {
    await this.connect();

    const result = await this.db.collection('users').deleteMany({
      $or: [
        { email: { $regex: /test.*@example\.com/i } },
        { email: { $regex: /.*-test@.*/i } },
        { email: { $regex: /.*\+test@.*/i } },
        { email: { $regex: /email-test@.*/i } },
        { email: { $regex: /flow-[abc]-.*/i } }, // Flow test users
        { email: { $regex: /new-user-check-.*/i } }, // Check-email test users
        { email: { $regex: /reset-email-test-.*/i } }, // Reset test users
      ]
    });

    return result.deletedCount;
  }

  /**
   * Clear all users (use with caution)
   */
  async clearAllUsers() {
    await this.connect();
    const result = await this.db.collection('users').deleteMany({});
    return result.deletedCount;
  }

  /**
   * Clear all sessions
   */
  async clearSessions() {
    await this.connect();
    const result = await this.db.collection('sessions').deleteMany({});
    return result.deletedCount;
  }

  /**
   * Clear all chats
   */
  async clearChats() {
    await this.connect();
    const result = await this.db.collection('chats').deleteMany({});
    return result.deletedCount;
  }

  /**
   * Clear all test data (users, sessions, chats)
   */
  async clearAllTestData() {
    await this.connect();

    const [users, sessions, chats] = await Promise.all([
      this.clearTestUsers(),
      this.clearSessions(),
      this.clearChats()
    ]);

    return { users, sessions, chats };
  }

  // ===========================================================================
  // QUERY OPERATIONS
  // ===========================================================================

  /**
   * Get user by email
   * @param {string} email - User email
   * @returns {Promise<object|null>} User document or null
   */
  async getUser(email) {
    await this.connect();
    return await this.db.collection('users').findOne({
      email: email.toLowerCase()
    });
  }

  /**
   * Get user by ID
   * @param {string} userId - User ID
   * @returns {Promise<object|null>} User document or null
   */
  async getUserById(userId) {
    await this.connect();
    const { ObjectId } = await import('mongodb');
    return await this.db.collection('users').findOne({
      _id: new ObjectId(userId)
    });
  }

  /**
   * Check if user exists
   * @param {string} email - User email
   * @returns {Promise<boolean>} True if user exists
   */
  async userExists(email) {
    const user = await this.getUser(email);
    return user !== null;
  }

  /**
   * Check if user is verified
   * @param {string} email - User email
   * @returns {Promise<boolean|null>} True if verified, null if user doesn't exist
   */
  async isUserVerified(email) {
    const user = await this.getUser(email);
    if (!user) return null;
    return user.email_verified === true;
  }

  /**
   * Check if user has password
   * @param {string} email - User email
   * @returns {Promise<boolean|null>} True if has password, null if user doesn't exist
   */
  async userHasPassword(email) {
    const user = await this.getUser(email);
    if (!user) return null;
    return user.password_hash !== undefined && user.password_hash !== null;
  }

  /**
   * Get user count
   * @param {object} query - MongoDB query filter (optional)
   * @returns {Promise<number>} Number of users matching query
   */
  async getUserCount(query = {}) {
    await this.connect();
    return await this.db.collection('users').countDocuments(query);
  }

  /**
   * Get all users (limited to 100)
   * @param {object} query - MongoDB query filter (optional)
   * @returns {Promise<Array>} Array of user documents
   */
  async getUsers(query = {}, limit = 100) {
    await this.connect();
    return await this.db.collection('users')
      .find(query)
      .limit(limit)
      .toArray();
  }

  // ===========================================================================
  // ASSERTION HELPERS
  // ===========================================================================

  /**
   * Assert user exists
   * @throws {Error} If user doesn't exist
   */
  async assertUserExists(email) {
    const exists = await this.userExists(email);
    if (!exists) {
      throw new Error(`Expected user ${email} to exist in database`);
    }
  }

  /**
   * Assert user doesn't exist
   * @throws {Error} If user exists
   */
  async assertUserNotExists(email) {
    const exists = await this.userExists(email);
    if (exists) {
      throw new Error(`Expected user ${email} to NOT exist in database`);
    }
  }

  /**
   * Assert user is verified
   * @throws {Error} If user doesn't exist or is not verified
   */
  async assertUserVerified(email) {
    const verified = await this.isUserVerified(email);
    if (verified === null) {
      throw new Error(`User ${email} does not exist`);
    }
    if (!verified) {
      throw new Error(`Expected user ${email} to be verified`);
    }
  }

  /**
   * Assert user is not verified
   * @throws {Error} If user doesn't exist or is verified
   */
  async assertUserNotVerified(email) {
    const verified = await this.isUserVerified(email);
    if (verified === null) {
      throw new Error(`User ${email} does not exist`);
    }
    if (verified) {
      throw new Error(`Expected user ${email} to NOT be verified`);
    }
  }

  /**
   * Assert user has password
   * @throws {Error} If user doesn't exist or has no password
   */
  async assertUserHasPassword(email) {
    const hasPassword = await this.userHasPassword(email);
    if (hasPassword === null) {
      throw new Error(`User ${email} does not exist`);
    }
    if (!hasPassword) {
      throw new Error(`Expected user ${email} to have a password`);
    }
  }

  // ===========================================================================
  // STATISTICS
  // ===========================================================================

  /**
   * Get database statistics
   * @returns {Promise<object>} Statistics object with collection counts
   */
  async getStats() {
    await this.connect();

    const collections = ['users', 'chats', 'chat_history', 'trips', 'sessions', 'counters'];
    const stats = {
      database: TEST_DB_CONFIG.dbName,
      collections: {},
      timestamp: new Date()
    };

    for (const collectionName of collections) {
      try {
        stats.collections[collectionName] = await this.db
          .collection(collectionName)
          .countDocuments();
      } catch (error) {
        stats.collections[collectionName] = 0;
      }
    }

    return stats;
  }
}

// ===========================================================================
// CONVENIENCE FUNCTIONS
// ===========================================================================

/**
 * Create and connect a database helper instance
 * @returns {Promise<DatabaseHelper>} Connected database helper
 */
export async function createDatabaseHelper() {
  const helper = new DatabaseHelper();
  await helper.connect();
  return helper;
}

/**
 * Execute database operation with automatic connection management
 * @param {Function} operation - Async function that receives DatabaseHelper
 * @returns {Promise<any>} Result of operation
 *
 * Example:
 * ```js
 * const user = await withDatabase(async (db) => {
 *   return await db.getUser('test@example.com');
 * });
 * ```
 */
export async function withDatabase(operation) {
  const helper = new DatabaseHelper();
  try {
    await helper.connect();
    return await operation(helper);
  } finally {
    await helper.disconnect();
  }
}
