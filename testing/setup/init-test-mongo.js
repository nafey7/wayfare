// MongoDB Test Database Initialization Script
//
// This script initializes the test database with proper indexes and collections
// for Playwright testing. It ensures a clean, consistent state for every test run.

print('=== Initializing Voya Test Database ===');

// Switch to the test database
db = db.getSiblingDB('voya_test');

print('Creating collections and indexes for test database...');

// Users collection with proper indexes
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "created_at": 1 });
db.users.createIndex({ "updated_at": 1 });
db.users.createIndex({ "is_verified": 1 });
db.users.createIndex({ "reset_token": 1, "reset_token_expires": 1 });

print('✅ Users collection indexes created');

// Chats collection with indexes
db.chats.createIndex({ "user_id": 1, "created_at": -1 });
db.chats.createIndex({ "created_at": 1 });
db.chats.createIndex({ "updated_at": 1 });

print('✅ Chats collection indexes created');

// Chat history collection
db.chat_history.createIndex({ "chat_id": 1, "timestamp": -1 });
db.chat_history.createIndex({ "user_id": 1, "timestamp": -1 });
db.chat_history.createIndex({ "timestamp": 1 });

print('✅ Chat history collection indexes created');

// Trips collection
db.trips.createIndex({ "user_id": 1, "created_at": -1 });
db.trips.createIndex({ "destination": 1 });
db.trips.createIndex({ "start_date": 1, "end_date": 1 });
db.trips.createIndex({ "status": 1 });

print('✅ Trips collection indexes created');

// Sessions collection (for JWT token management)
db.sessions.createIndex({ "user_id": 1 });
db.sessions.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
db.sessions.createIndex({ "refresh_token": 1 });

print('✅ Sessions collection indexes created');

// Passengers collection (profile page, stored passenger details)
// Unique partial index: at most one primary passenger per user (prevents race condition)
db.passengers.createIndex({ "user_id": 1 });
db.passengers.createIndex(
  { "user_id": 1, "is_primary": 1 },
  { unique: true, partialFilterExpression: { "is_primary": true } }
);

print('✅ Passengers collection indexes created');

// User preferences collection (profile page)
db.user_preferences.createIndex({ "user_id": 1 }, { unique: true });

print('✅ User preferences collection indexes created');

// Counters collection for auto-incrementing IDs
db.counters.insertOne({
    "_id": "user_id",
    "sequence_value": 1000
});

db.counters.insertOne({
    "_id": "chat_id",
    "sequence_value": 1000
});

db.counters.insertOne({
    "_id": "trip_id",
    "sequence_value": 1000
});

print('✅ Counter sequences initialized');

// Create test data cleanup function
db.system.js.save({
    _id: "cleanupTestData",
    value: function() {
        print("🧹 Starting test data cleanup...");

        // Remove all test users (keep any admin users if they exist)
        const userDeleteResult = db.users.deleteMany({
            "email": { $regex: /test.*@example\.com|.*-test@.*/ }
        });
        print(`   - Deleted ${userDeleteResult.deletedCount} test users`);

        // Remove all test chats
        const chatDeleteResult = db.chats.deleteMany({});
        print(`   - Deleted ${chatDeleteResult.deletedCount} chat records`);

        // Remove all test chat history
        const historyDeleteResult = db.chat_history.deleteMany({});
        print(`   - Deleted ${historyDeleteResult.deletedCount} chat history records`);

        // Remove all test trips
        const tripDeleteResult = db.trips.deleteMany({});
        print(`   - Deleted ${tripDeleteResult.deletedCount} trip records`);

        // Remove all test sessions
        const sessionDeleteResult = db.sessions.deleteMany({});
        print(`   - Deleted ${sessionDeleteResult.deletedCount} session records`);

        // Reset counters to base values
        db.counters.updateOne(
            { "_id": "user_id" },
            { $set: { "sequence_value": 1000 } }
        );
        db.counters.updateOne(
            { "_id": "chat_id" },
            { $set: { "sequence_value": 1000 } }
        );
        db.counters.updateOne(
            { "_id": "trip_id" },
            { $set: { "sequence_value": 1000 } }
        );

        print("✅ Test data cleanup completed");

        return {
            users_deleted: userDeleteResult.deletedCount,
            chats_deleted: chatDeleteResult.deletedCount,
            history_deleted: historyDeleteResult.deletedCount,
            trips_deleted: tripDeleteResult.deletedCount,
            sessions_deleted: sessionDeleteResult.deletedCount
        };
    }
});

print('✅ Test data cleanup function installed');

// Create test user setup function
db.system.js.save({
    _id: "createTestUser",
    value: function(email, firstName = "Test", lastName = "User") {
        const user = {
            email: email,
            first_name: firstName,
            last_name: lastName,
            is_verified: false,
            is_active: true,
            created_at: new Date(),
            updated_at: new Date(),
            profile: {
                preferences: {},
                settings: {}
            }
        };

        const result = db.users.insertOne(user);
        print(`✅ Created test user: ${email} with ID: ${result.insertedId}`);

        return {
            user_id: result.insertedId,
            email: email
        };
    }
});

print('✅ Test user creation function installed');

// Create database stats function for debugging
db.system.js.save({
    _id: "getTestDatabaseStats",
    value: function() {
        const stats = {
            database: "voya_test",
            collections: {},
            timestamp: new Date()
        };

        const collections = ["users", "chats", "chat_history", "trips", "sessions", "counters", "passengers", "user_preferences"];

        collections.forEach(function(collName) {
            try {
                stats.collections[collName] = db[collName].countDocuments();
            } catch (e) {
                stats.collections[collName] = 0;
            }
        });

        return stats;
    }
});

print('✅ Database stats function installed');

// Verify database setup
const stats = db.getTestDatabaseStats();
print('📊 Initial database statistics:');
print(JSON.stringify(stats, null, 2));

print('=== Test Database Initialization Complete ===');
print('');
print('Available test helper functions:');
print('  - db.cleanupTestData()          // Clean all test data');
print('  - db.createTestUser(email)      // Create a test user');
print('  - db.getTestDatabaseStats()     // Get collection counts');
print('');
print('💡 Use these functions in your test setup and teardown scripts');
