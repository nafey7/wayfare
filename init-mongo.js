// Initialize MongoDB for Voya development
print('Initializing Voya database...');

// Create database
db = db.getSiblingDB('voya_dev');

// Create collections if they don't exist
db.createCollection('users');
db.createCollection('trips');
db.createCollection('chats');
db.createCollection('chat_history');
db.createCollection('sessions');
db.createCollection('passengers');
db.createCollection('user_preferences');
// Flight/hotel booking rows (see app.database.constants.BOOKING_EVENT_COLLECTION); indexes from migrations
db.createCollection('booking_events');

// Create indexes for better performance
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "google_id": 1 }, { sparse: true, unique: true });
db.chats.createIndex({ "user_id": 1 });
db.chat_history.createIndex({ "chat_id": 1 });
db.chat_history.createIndex({ "timestamp": 1 });
db.passengers.createIndex({ "user_id": 1 });
db.passengers.createIndex(
  { "user_id": 1, "is_primary": 1 },
  { unique: true, partialFilterExpression: { "is_primary": true } }
);
db.user_preferences.createIndex({ "user_id": 1 }, { unique: true });

print('Voya database initialized successfully!');
