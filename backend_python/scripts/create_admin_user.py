#!/usr/bin/env python3
"""
Script to create a test admin user in the database.
Run this script to add testadmin@example.com as an admin user.
"""

import asyncio
import logging
from datetime import datetime

from app.database.connection import connect_to_mongodb, get_connection
from app.domains.auth.service import AuthService
from app.domains.user.enums import UserRole, UserStatus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_admin_user():
    """Create the test admin user"""

    # Admin user details
    admin_email = "testadmin@example.com"
    admin_password = "Admin1234!"  # noqa: S105 - Test admin password for development

    try:
        # Connect to database
        logger.info("Connecting to database...")
        await connect_to_mongodb()

        # Get users collection
        db = get_connection().get_database()
        users_collection = db.users

        # Check if admin user already exists
        existing_user = await users_collection.find_one({"email": admin_email})
        if existing_user:
            logger.info(f"Admin user {admin_email} already exists!")
            return

        # Hash the password
        password_hash = AuthService.hash_password(admin_password)

        # Create admin user document
        admin_user = {
            "email": admin_email,
            "password_hash": password_hash,
            "first_name": "Test",
            "last_name": "Admin",
            "auth_provider": "local",
            "email_verified": True,
            "status": UserStatus.ACTIVE.value,
            "role": UserRole.ADMIN.value,
            "failed_login_attempts": 0,
            "last_login": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "profile_image": None,
            "mobile": None,
            "address": None,
            "google_id": None,
            "facebook_id": None,
            "email_verification_token": None,
            "password_reset_token": None,
            "password_reset_expires": None,
        }

        # Insert the admin user
        result = await users_collection.insert_one(admin_user)

        if result.inserted_id:
            logger.info(f"✅ Successfully created admin user: {admin_email}")
            logger.info(f"   Password: {admin_password}")
            logger.info(f"   Role: {UserRole.ADMIN.value}")
            logger.info(f"   User ID: {result.inserted_id}")
        else:
            logger.error("❌ Failed to create admin user")

    except Exception as e:
        logger.error(f"❌ Error creating admin user: {e}")
        raise


if __name__ == "__main__":
    print("🔧 Creating test admin user...")
    print("   Email: testadmin@example.com")
    print("   Password: Admin1234!")
    print("   Role: admin")
    print()

    asyncio.run(create_admin_user())

    print()
    print("✅ Script completed!")
    print("You can now use these credentials to login as admin.")
