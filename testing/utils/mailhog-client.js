/**
 * MailHog Client
 *
 * Unified MailHog API client for email testing across all test types.
 * Allows testing of email delivery, content, and links.
 *
 * Enhanced with retry mechanisms, better error handling, and test environment support.
 */

import { URLS } from './constants.js';

// Configure MailHog URL based on environment
const getMailHogBaseUrl = () => {
  if (process.env.NODE_ENV === 'testing' || process.env.ENVIRONMENT === 'testing') {
    return process.env.MAILHOG_WEB_URL || 'http://localhost:8026';
  }
  return URLS.MAILHOG;
};

const MAILHOG_BASE_URL = getMailHogBaseUrl();

class MailHogHelper {
  constructor(request) {
    this.request = request;
  }

  /**
   * Get all emails from MailHog with retry logic
   */
  async getAllEmails(retries = 3) {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const response = await this.request.get(`${MAILHOG_BASE_URL}/api/v2/messages`);
        if (response.ok()) {
          const data = await response.json();
          return data;
        }

        if (attempt === retries) {
          throw new Error(`Failed to fetch emails after ${retries} attempts: ${response.status()}`);
        }

        console.log(`⚠️ MailHog request failed (attempt ${attempt}/${retries}), retrying...`);
        await this._delay(1000 * attempt); // Exponential backoff

      } catch (error) {
        if (attempt === retries) {
          throw new Error(`MailHog connection failed after ${retries} attempts: ${error.message}`);
        }
        console.log(`⚠️ MailHog connection error (attempt ${attempt}/${retries}), retrying...`);
        await this._delay(1000 * attempt);
      }
    }
  }

  /**
   * Utility method for delays
   */
  async _delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Clear all emails from MailHog
   */
  async clearEmails() {
    const response = await this.request.delete(`${MAILHOG_BASE_URL}/api/v1/messages`);
    if (!response.ok()) {
      throw new Error(`Failed to clear emails: ${response.status()}`);
    }
  }

  /**
   * Wait for a new email to arrive (polls MailHog)
   * Enhanced with better matching and debugging
   * @param {string} toEmail - Email address to wait for
   * @param {Object} options - Configuration options
   */
  async waitForEmail(toEmail, options = {}) {
    const {
      timeout = 20000,        // Increased default timeout
      pollInterval = 2000,    // Increased poll interval
      retries = 3,            // Retry attempts for each poll
      subject = null,         // Optional subject filter
      debug = false           // Debug logging
    } = options;

    const startTime = Date.now();
    let pollCount = 0;

    if (debug) {
      console.log(`🔍 Waiting for email to: ${toEmail}`);
      console.log(`   Timeout: ${timeout}ms, Poll interval: ${pollInterval}ms`);
    }

    while (Date.now() - startTime < timeout) {
      pollCount++;

      try {
        const emails = await this.getAllEmails(retries);

        if (debug && pollCount % 5 === 0) {
          console.log(`   Poll #${pollCount}: Found ${emails.items?.length || 0} total emails`);
        }

        // Enhanced email matching
        const targetEmail = emails.items?.find(email => {
          const recipients = email.To || [];
          const emailDomain = toEmail.split('@')[1];
          const emailUser = toEmail.split('@')[0];

          // Check if email matches recipient
          const recipientMatch = recipients.some(recipient => {
            const recipientFull = `${recipient.Mailbox}@${recipient.Domain}`;
            return recipientFull.toLowerCase() === toEmail.toLowerCase() ||
                   recipient.Mailbox.toLowerCase() === emailUser.toLowerCase();
          });

          // Optional subject filtering
          if (subject && recipientMatch) {
            const emailSubject = email.Content?.Headers?.Subject?.[0] || '';
            return emailSubject.toLowerCase().includes(subject.toLowerCase());
          }

          return recipientMatch;
        });

        if (targetEmail) {
          if (debug) {
            console.log(`✅ Found email after ${pollCount} polls (${Date.now() - startTime}ms)`);
            console.log(`   Subject: ${targetEmail.Content?.Headers?.Subject?.[0] || 'No subject'}`);
          }
          return targetEmail;
        }

        // Wait before next poll
        await this._delay(pollInterval);

      } catch (error) {
        console.log(`⚠️ Error during email polling (attempt ${pollCount}): ${error.message}`);
        await this._delay(pollInterval);
      }
    }

    throw new Error(`Timeout waiting for email to ${toEmail} after ${timeout}ms (${pollCount} polls attempted)`);
  }

  /**
   * Get the latest email sent to a specific address
   * @param {string} toEmail - Email address
   */
  async getLatestEmailTo(toEmail) {
    const emails = await this.getAllEmails();

    const userEmails = emails.items?.filter(email => {
      const recipients = email.To || [];
      return recipients.some(recipient => recipient.Mailbox === toEmail.split('@')[0]);
    });

    if (!userEmails || userEmails.length === 0) {
      return null;
    }

    // Sort by date and return the latest
    return userEmails.sort((a, b) => new Date(b.Created) - new Date(a.Created))[0];
  }

  /**
   * Extract 6-digit OTP from PII verification email body.
   * Decodes base64/multipart content so the OTP is found in the actual HTML, not raw MIME.
   * @param {Object} email - Email object from MailHog
   * @returns {string|null} - 6-digit OTP or null
   */
  extractPiiVerificationOtp(email) {
    const content = email?.Content;
    let body = content?.Body || '';

    // Decode base64 parts (multipart emails) so we search the real content, not raw MIME
    if (body.includes('base64')) {
      const base64Patterns = [
        /Content-Transfer-Encoding:\s*base64\r?\n\r?\n([A-Za-z0-9+/=\r\n\s]+?)(?=\r?\n--|\r?\nContent-|$)/gi,
        /base64\r?\n\r?\n([A-Za-z0-9+/=\r\n\s]+?)(?=\r?\n--|\r?\nContent-|$)/gi,
      ];
      for (const pattern of base64Patterns) {
        let match;
        while ((match = pattern.exec(body)) !== null) {
          try {
            const base64Content = match[1].replace(/\r?\n/g, '').replace(/\s/g, '').trim();
            if (base64Content.length > 0) {
              body += ' ' + Buffer.from(base64Content, 'base64').toString('utf8');
            }
          } catch {
            /* skip decode errors */
          }
        }
      }
    }
    // Also extract from text/html parts without base64
    if (body.includes('Content-Type:') && body.includes('text/html')) {
      const htmlParts = body.match(/Content-Type:\s*text\/html[^]*?(?=\r?\n--|\r?\nContent-|$)/gi);
      if (htmlParts) {
        for (const part of htmlParts) {
          const htmlMatch = part.match(/\r?\n\r?\n([^]*)/);
          if (htmlMatch) body += ' ' + htmlMatch[1];
        }
      }
    }

    // Target the OTP in its styled <p> (letter-spacing: 4px) to avoid matching other 6-digit numbers
    const match = body.match(/letter-spacing[^>]*>(\d{6})</);
    return match ? match[1] : null;
  }

  /**
   * Extract links from email HTML content
   * Enhanced version with comprehensive parsing strategies
   * @param {Object} email - Email object from MailHog
   */
  extractLinksFromEmail(email) {
    const content = email.Content;
    const body = content.Body || '';
    const headers = content.Headers || {};

    // Initialize with original body content
    let textContent = body;
    let htmlContent = '';

    // console.log('🔍 DEBUG: Email content analysis:');
    // console.log('   Body length:', body.length);
    // console.log('   Contains base64:', body.includes('base64'));
    // console.log('   Content-Type:', headers['Content-Type'] || 'Not specified');

    // Strategy 1: Extract from multipart base64 encoded content
    if (body.includes('base64')) {
      try {
        // Enhanced base64 extraction with better patterns
        const base64Patterns = [
          /Content-Transfer-Encoding:\s*base64\r?\n\r?\n([A-Za-z0-9+\/=\r\n\s]+?)(?=\r?\n--|\r?\nContent-|$)/gi,
          /base64\r?\n\r?\n([A-Za-z0-9+\/=\r\n\s]+?)(?=\r?\n--|\r?\nContent-|$)/gi,
          /Content-Transfer-Encoding:\s*base64[^\n]*\n([A-Za-z0-9+\/=\r\n\s]+)/gi
        ];

        for (const pattern of base64Patterns) {
          let match;
          while ((match = pattern.exec(body)) !== null) {
            try {
              // Clean the base64 content
              const base64Content = match[1]
                .replace(/\r?\n/g, '')
                .replace(/\s/g, '')
                .trim();

              if (base64Content.length > 0) {
                const decoded = Buffer.from(base64Content, 'base64').toString('utf8');
                // console.log('   ✅ Successfully decoded base64 content, length:', decoded.length);
                textContent += ' ' + decoded;
                htmlContent += ' ' + decoded;
              }
            } catch (e) {
              // console.log('   ⚠️ Base64 decode error:', e.message);
            }
          }
        }
      } catch (e) {
        // console.log('   ⚠️ Base64 extraction error:', e.message);
      }
    }

    // Strategy 2: Extract from multipart content without base64
    if (body.includes('Content-Type:')) {
      try {
        const htmlParts = body.match(/Content-Type:\s*text\/html[^]*?(?=\r?\n--|\r?\nContent-|$)/gi);
        if (htmlParts) {
          for (const part of htmlParts) {
            const htmlMatch = part.match(/\r?\n\r?\n([^]*)/);
            if (htmlMatch) {
              htmlContent += ' ' + htmlMatch[1];
              textContent += ' ' + htmlMatch[1];
              // console.log('   ✅ Extracted HTML part, length:', htmlMatch[1].length);
            }
          }
        }
      } catch (e) {
        // console.log('   ⚠️ HTML part extraction error:', e.message);
      }
    }

    // Strategy 3: Enhanced link extraction with comprehensive patterns
    const patterns = [
      // HTML href patterns
      /href\s*=\s*["']([^"']+?)["']/gi,                    // Standard href
      /href\s*=\s*([^\s>]+)/gi,                            // href without quotes

      // URL patterns in various contexts
      /https?:\/\/[^\s<>"{}|\\^`[\]()]+/gi,               // Plain URLs
      /<a[^>]+href\s*=\s*["']([^"']+)["'][^>]*>/gi,       // Anchor tags
      /=3D"(https?:\/\/[^"]+)"/gi,                        // Quoted-printable encoded URLs
      /=3D(https?:\/\/[^\s=]+)/gi,                        // Quoted-printable URLs

      // Email-specific patterns
      /(?:https?:\/\/)?localhost:\d+[^\s<>"{}|\\^`[\]()]*/gi,  // Local development URLs
      /click[^:]*:\s*(https?:\/\/[^\s<>"{}|\\^`[\]()]+)/gi,     // "Click here:" patterns
    ];

    const links = [];
    const processedContent = textContent + ' ' + htmlContent;

    // console.log('   🔍 Processing content length:', processedContent.length);

    for (let i = 0; i < patterns.length; i++) {
      const pattern = patterns[i];
      let match;
      let matchCount = 0;

      // Reset regex lastIndex to avoid state issues
      pattern.lastIndex = 0;

      while ((match = pattern.exec(processedContent)) !== null) {
        matchCount++;
        const url = match[1] || match[0]; // Use captured group or full match

        if (url && url.length > 0) {
          // Clean and normalize the URL
          let cleanUrl = url
            .replace(/=3D/g, '=')     // Decode quoted-printable
            .replace(/=\r?\n/g, '')   // Remove soft line breaks
            .replace(/\s+$/, '')      // Remove trailing whitespace
            .trim();

          // Only add valid URLs
          if (cleanUrl.length > 0 && !links.includes(cleanUrl)) {
            links.push(cleanUrl);
            // console.log(`   ✅ Found link (pattern ${i + 1}):`, cleanUrl);
          }
        }

        // Prevent infinite loops
        if (matchCount > 100) break;
      }
    }

    // console.log('   📊 Total links extracted:', links.length);
    // console.log('   🔗 Links:', links);

    return links;
  }

  /**
   * Extract password reset token from email
   * Enhanced with comprehensive link matching and debugging
   * @param {Object} email - Email object from MailHog
   */
  extractPasswordResetToken(email) {
    console.log('🔑 DEBUG: Extracting password reset token...');
    const links = this.extractLinksFromEmail(email);

    console.log('🔍 DEBUG: Searching for reset links in:', links.length, 'total links');

    // Enhanced pattern matching for reset links
    const resetLink = links.find(link => {
      const linkLower = link.toLowerCase();

      // Multiple patterns to match reset links
      const hasResetPath = linkLower.includes('/reset-password') ||
                          linkLower.includes('reset-password') ||
                          linkLower.includes('/password/reset') ||
                          linkLower.includes('password-reset');

      const hasToken = linkLower.includes('token=') ||
                      linkLower.includes('t=') ||
                      linkLower.includes('reset=');

      console.log(`   🔍 Checking link: "${link}"`);
      console.log(`      - Has reset path: ${hasResetPath}`);
      console.log(`      - Has token: ${hasToken}`);

      return hasResetPath && hasToken;
    });

    if (!resetLink) {
      console.log('❌ DEBUG: No reset link found in email');
      console.log('   Available links:', links);
      return null;
    }

    console.log('✅ DEBUG: Found reset link:', resetLink);

    // Enhanced token extraction with multiple patterns
    const tokenPatterns = [
      /token=([^&\s#]+)/i,      // Standard token parameter
      /t=([^&\s#]+)/i,          // Short token parameter
      /reset=([^&\s#]+)/i,      // Alternative token parameter
      /\/([a-zA-Z0-9_-]{20,})/  // Token as path segment (long alphanumeric)
    ];

    let token = null;

    for (const pattern of tokenPatterns) {
      const match = resetLink.match(pattern);
      if (match && match[1]) {
        token = match[1];
        console.log(`✅ DEBUG: Token extracted with pattern ${pattern}:`, token);
        break;
      }
    }

    if (!token) {
      console.log('❌ DEBUG: No token found in reset link:', resetLink);
      return null;
    }

    // URL decode the token in case it's encoded
    try {
      const decodedToken = decodeURIComponent(token);
      if (decodedToken !== token) {
        console.log('🔄 DEBUG: Token was URL encoded, decoded:', decodedToken);
        token = decodedToken;
      }
    } catch (e) {
      console.log('⚠️ DEBUG: Token decode failed, using as-is:', e.message);
    }

    console.log('🔑 DEBUG: Final extracted token:', token);
    return token;
  }

  /**
   * Extract registration completion token from email
   * Enhanced with comprehensive link matching and debugging
   * @param {Object} email - Email object from MailHog
   */
  extractRegistrationToken(email) {
    console.log('📝 DEBUG: Extracting registration token...');
    const links = this.extractLinksFromEmail(email);

    console.log('🔍 DEBUG: Searching for registration links in:', links.length, 'total links');

    // Enhanced pattern matching for registration links
    const registrationLink = links.find(link => {
      const linkLower = link.toLowerCase();

      // Multiple patterns to match registration links
      const hasRegistrationPath = linkLower.includes('/complete-registration') ||
                                 linkLower.includes('complete-registration') ||
                                 linkLower.includes('/register/complete') ||
                                 linkLower.includes('/activation') ||
                                 linkLower.includes('/verify');

      const hasToken = linkLower.includes('token=') ||
                      linkLower.includes('t=') ||
                      linkLower.includes('activation=') ||
                      linkLower.includes('verify=');

      console.log(`   🔍 Checking link: "${link}"`);
      console.log(`      - Has registration path: ${hasRegistrationPath}`);
      console.log(`      - Has token: ${hasToken}`);

      return hasRegistrationPath && hasToken;
    });

    if (!registrationLink) {
      console.log('❌ DEBUG: No registration link found in email');
      console.log('   Available links:', links);
      return null;
    }

    console.log('✅ DEBUG: Found registration link:', registrationLink);

    // Enhanced token extraction with multiple patterns
    const tokenPatterns = [
      /token=([^&\s#]+)/i,         // Standard token parameter
      /t=([^&\s#]+)/i,             // Short token parameter
      /activation=([^&\s#]+)/i,    // Activation token parameter
      /verify=([^&\s#]+)/i,        // Verify token parameter
      /\/([a-zA-Z0-9_-]{20,})/     // Token as path segment (long alphanumeric)
    ];

    let token = null;

    for (const pattern of tokenPatterns) {
      const match = registrationLink.match(pattern);
      if (match && match[1]) {
        token = match[1];
        console.log(`✅ DEBUG: Token extracted with pattern ${pattern}:`, token);
        break;
      }
    }

    if (!token) {
      console.log('❌ DEBUG: No token found in registration link:', registrationLink);
      return null;
    }

    // URL decode the token in case it's encoded
    try {
      const decodedToken = decodeURIComponent(token);
      if (decodedToken !== token) {
        console.log('🔄 DEBUG: Token was URL encoded, decoded:', decodedToken);
        token = decodedToken;
      }
    } catch (e) {
      console.log('⚠️ DEBUG: Token decode failed, using as-is:', e.message);
    }

    console.log('📝 DEBUG: Final extracted registration token:', token);
    return token;
  }

  /**
   * Verify that email contains expected content
   * @param {Object} email - Email object from MailHog
   * @param {Object} expectations - Object with expected properties
   */
  verifyEmailContent(email, expectations) {
    const content = email.Content;
    const body = content.Body || '';
    const headers = content.Headers || {};

    const results = {
      valid: true,
      errors: []
    };

    // Check subject
    if (expectations.subject) {
      const subject = headers.Subject?.[0] || '';
      if (!subject.toLowerCase().includes(expectations.subject.toLowerCase())) {
        results.valid = false;
        results.errors.push(`Expected subject to contain "${expectations.subject}", got "${subject}"`);
      }
    }

    // Check body contains text
    if (expectations.bodyContains) {
      const textToCheck = Array.isArray(expectations.bodyContains)
        ? expectations.bodyContains
        : [expectations.bodyContains];

      for (const text of textToCheck) {
        if (!body.toLowerCase().includes(text.toLowerCase())) {
          results.valid = false;
          results.errors.push(`Expected body to contain "${text}"`);
        }
      }
    }

    // Check links
    if (expectations.hasLinks) {
      const links = this.extractLinksFromEmail(email);
      const expectedLinks = Array.isArray(expectations.hasLinks)
        ? expectations.hasLinks
        : [expectations.hasLinks];

      for (const expectedLink of expectedLinks) {
        const hasLink = links.some(link => link.includes(expectedLink));
        if (!hasLink) {
          results.valid = false;
          results.errors.push(`Expected email to contain link with "${expectedLink}"`);
        }
      }
    }

    return results;
  }
}

export { MailHogHelper };
