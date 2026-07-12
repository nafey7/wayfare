/**
 * API Client
 *
 * Centralized API request utilities for testing
 * Provides consistent interface for backend API interactions
 */

import { URLS, buildApiUrl } from './constants.js';

// =============================================================================
// API CLIENT CLASS
// =============================================================================

export class ApiClient {
  constructor(request) {
    this.request = request;
    this.baseUrl = URLS.BACKEND;
  }

  // ===========================================================================
  // AUTHENTICATION ENDPOINTS
  // ===========================================================================

  async checkEmail(email) {
    return await this.request.post(buildApiUrl(URLS.AUTH.CHECK_EMAIL), {
      data: { email }
    });
  }

  async register(userData) {
    return await this.request.post(buildApiUrl(URLS.AUTH.REGISTER), {
      data: userData
    });
  }

  async login(email, password, fingerprint = null) {
    return await this.request.post(buildApiUrl(URLS.AUTH.LOGIN), {
      data: { email, password, fingerprint }
    });
  }

  async logout(authToken) {
    return await this.request.post(buildApiUrl(URLS.AUTH.LOGOUT), {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
  }

  async forgotPassword(email) {
    return await this.request.post(buildApiUrl(URLS.AUTH.FORGOT_PASSWORD), {
      data: { email }
    });
  }

  async resetPassword(token, newPassword) {
    return await this.request.post(buildApiUrl(URLS.AUTH.RESET_PASSWORD), {
      data: { token, new_password: newPassword }
    });
  }

  async validateResetToken(token) {
    return await this.request.post(buildApiUrl(URLS.AUTH.VALIDATE_RESET_TOKEN), {
      data: { token }
    });
  }

  async completeRegistration(token, password, confirmPassword) {
    return await this.request.post(buildApiUrl(URLS.AUTH.COMPLETE_REGISTRATION), {
      data: {
        token,
        password,
        confirm_password: confirmPassword
      }
    });
  }

  async refreshToken(refreshToken) {
    return await this.request.post(buildApiUrl(URLS.AUTH.REFRESH), {
      data: { refresh_token: refreshToken }
    });
  }

  async getGoogleConfig() {
    return await this.request.get(buildApiUrl(URLS.AUTH.CONFIG_GOOGLE));
  }

  // ===========================================================================
  // CHAT ENDPOINTS
  // ===========================================================================

  async sendChatMessage(message, authToken, chatId = null) {
    return await this.request.post(buildApiUrl(URLS.CHAT.MESSAGE), {
      data: { message, chat_id: chatId },
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
  }

  // ===========================================================================
  // HEALTH & STATUS
  // ===========================================================================

  async getHealth() {
    return await this.request.get(buildApiUrl(URLS.HEALTH));
  }

  // ===========================================================================
  // HELPER METHODS
  // ===========================================================================

  /**
   * Make authenticated request
   */
  async authenticatedRequest(method, endpoint, authToken, data = null) {
    const config = {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    };

    if (data) {
      config.data = data;
    }

    const url = buildApiUrl(endpoint);

    switch (method.toLowerCase()) {
      case 'get':
        return await this.request.get(url, config);
      case 'post':
        return await this.request.post(url, config);
      case 'put':
        return await this.request.put(url, config);
      case 'delete':
        return await this.request.delete(url, config);
      default:
        throw new Error(`Unsupported HTTP method: ${method}`);
    }
  }

  /**
   * Check if response indicates success
   */
  isSuccessResponse(response) {
    return response.ok() && response.status() >= 200 && response.status() < 300;
  }

  /**
   * Get response JSON with error handling
   */
  async getResponseJson(response) {
    try {
      return await response.json();
    } catch (error) {
      console.warn('Failed to parse response as JSON:', error);
      return null;
    }
  }

  /**
   * Validate response status and return JSON
   */
  async validateAndGetJson(response, expectedStatus = 200) {
    if (response.status() !== expectedStatus) {
      const errorText = await response.text();
      throw new Error(`Expected status ${expectedStatus}, got ${response.status()}: ${errorText}`);
    }

    return await this.getResponseJson(response);
  }
}

// =============================================================================
// CONVENIENCE FUNCTIONS
// =============================================================================

/**
 * Create API client instance
 */
export function createApiClient(request) {
  return new ApiClient(request);
}

/**
 * Test API health
 */
export async function testApiHealth(request) {
  const client = createApiClient(request);

  try {
    const response = await client.getHealth();
    return {
      healthy: client.isSuccessResponse(response),
      status: response.status(),
      response
    };
  } catch (error) {
    return {
      healthy: false,
      error: error.message
    };
  }
}