/**
 * Global Test Setup
 *
 * This script runs once before all tests to prepare the test environment.
 * It ensures the test database is ready and services are accessible.
 */

import { setupTestDatabase, verifyTestDatabase } from './database-cleanup.js';

async function globalSetup() {
  console.log('🚀 Starting global test setup...');

  try {
    // Verify test environment configuration
    console.log('📋 Verifying test environment...');
    const requiredEnvVars = [
      'DATABASE_NAME',
      'FRONTEND_URL',
      'VITE_API_URL'
    ];

    for (const envVar of requiredEnvVars) {
      if (!process.env[envVar]) {
        console.warn(`⚠️ Missing environment variable: ${envVar}`);
      } else {
        console.log(`✅ ${envVar}: ${process.env[envVar]}`);
      }
    }

    // Verify test database connection and setup
    console.log('🔌 Setting up test database...');
    await setupTestDatabase();

    // Verify test services are accessible
    console.log('🌐 Verifying test services...');
    await verifyTestServices();

    console.log('✅ Global test setup completed successfully');

  } catch (error) {
    console.error('❌ Global test setup failed:', error);
    process.exit(1);
  }
}

/**
 * Verify that all test services are accessible
 */
async function verifyTestServices() {
  const services = [
    {
      name: 'Frontend',
      url: process.env.FRONTEND_URL || 'http://localhost:8001',
      timeout: 10000
    },
    {
      name: 'Backend API',
      url: (process.env.VITE_API_URL || 'http://localhost:8001/api').replace('/api', '/health'),
      timeout: 10000
    },
    {
      name: 'MailHog',
      url: process.env.MAILHOG_WEB_URL || 'http://localhost:8026',
      timeout: 5000
    }
  ];

  for (const service of services) {
    try {
      console.log(`   Checking ${service.name} at ${service.url}...`);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), service.timeout);

      const response = await fetch(service.url, {
        signal: controller.signal,
        headers: {
          'User-Agent': 'Playwright Test Setup'
        }
      });

      clearTimeout(timeoutId);

      if (response.ok || response.status < 500) {
        console.log(`   ✅ ${service.name} is accessible`);
      } else {
        console.log(`   ⚠️ ${service.name} returned status ${response.status} (continuing anyway)`);
      }

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log(`   ⚠️ ${service.name} timeout after ${service.timeout}ms (continuing anyway)`);
      } else {
        console.log(`   ⚠️ ${service.name} check failed: ${error.message} (continuing anyway)`);
      }
    }
  }
}

export default globalSetup;
