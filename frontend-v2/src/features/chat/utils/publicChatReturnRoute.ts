/**
 * Stash the authenticated equivalent of a public chat content route so post–email-verification
 * flows (e.g. CompleteRegistrationPage) can redirect there after `/complete-registration`.
 */

const PUBLIC_CHAT_RETURN_TO_KEY = 'voya_public_chat_return_to';

/** 24-hour TTL for stashed return path. */
const TTL_MS = 24 * 60 * 60 * 1000;

export interface PublicChatReturnToEnvelope {
  /** Authenticated equivalent path, e.g. '/flights/recommendations' */
  path: string;
  /** Optional search string including `?` prefix */
  search?: string;
  timestamp: number;
}

function isValidReturnPath(path: string): boolean {
  return (
    path.startsWith('/flights') ||
    path.startsWith('/hotels') ||
    path.startsWith('/itinerary')
  );
}

function buildFullPath(envelope: PublicChatReturnToEnvelope): string {
  const search = envelope.search ?? '';
  return `${envelope.path}${search}`;
}

function readEnvelope(raw: string): PublicChatReturnToEnvelope | null {
  let envelope: PublicChatReturnToEnvelope;
  try {
    envelope = JSON.parse(raw) as PublicChatReturnToEnvelope;
  } catch {
    return null;
  }
  if (!envelope?.path || typeof envelope.path !== 'string') return null;
  if (!isValidReturnPath(envelope.path)) return null;
  if (typeof envelope.timestamp !== 'number') return null;
  if (Date.now() - envelope.timestamp > TTL_MS) return null;
  if (envelope.search !== undefined && typeof envelope.search !== 'string') {
    return null;
  }
  return envelope;
}

/**
 * Store return-to path (validated). No-op if path is not an allowed authenticated content route.
 */
export function stashPublicChatReturnTo(path: string, search?: string): void {
  if (!isValidReturnPath(path)) return;
  try {
    const envelope: PublicChatReturnToEnvelope = {
      path,
      timestamp: Date.now(),
      ...(search && search.length > 0 ? { search } : {}),
    };
    localStorage.setItem(PUBLIC_CHAT_RETURN_TO_KEY, JSON.stringify(envelope));
  } catch {
    // private browsing, quota, etc.
  }
}

/**
 * Read return-to without removing. Returns null if missing, invalid, or expired.
 * Removes the key when data is invalid or expired so stale entries do not linger.
 */
export function peekPublicChatReturnTo(): string | null {
  try {
    const raw = localStorage.getItem(PUBLIC_CHAT_RETURN_TO_KEY);
    if (!raw) return null;
    const envelope = readEnvelope(raw);
    if (!envelope) {
      localStorage.removeItem(PUBLIC_CHAT_RETURN_TO_KEY);
      return null;
    }
    return buildFullPath(envelope);
  } catch {
    try {
      localStorage.removeItem(PUBLIC_CHAT_RETURN_TO_KEY);
    } catch {
      // ignore
    }
    return null;
  }
}

/**
 * Read return-to, validate, remove key, and return full path or null.
 * Removes the key only after a valid envelope is read (invalid/expired data is cleared separately).
 */
export function consumePublicChatReturnTo(): string | null {
  try {
    const raw = localStorage.getItem(PUBLIC_CHAT_RETURN_TO_KEY);
    if (!raw) return null;
    const envelope = readEnvelope(raw);
    if (!envelope) {
      localStorage.removeItem(PUBLIC_CHAT_RETURN_TO_KEY);
      return null;
    }
    localStorage.removeItem(PUBLIC_CHAT_RETURN_TO_KEY);
    return buildFullPath(envelope);
  } catch {
    try {
      localStorage.removeItem(PUBLIC_CHAT_RETURN_TO_KEY);
    } catch {
      // ignore
    }
    return null;
  }
}

export function clearPublicChatReturnTo(): void {
  try {
    localStorage.removeItem(PUBLIC_CHAT_RETURN_TO_KEY);
  } catch {
    // ignore
  }
}
