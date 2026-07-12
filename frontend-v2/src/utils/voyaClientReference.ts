/** Matches backend VoyaReferenceGenerator.ALPHABET (no 0/O/1/I). */
const VOYA_ID_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

/**
 * Client-side VOYA-XXXXXXXXXX reference for voucher checkout (flight/hotel).
 * Uniqueness is probabilistic; backend also accepts this as create-order metadata.
 */
export function generateClientVoyaReference(): string {
  const bytes = new Uint8Array(10);
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i++) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  let id = '';
  for (let i = 0; i < 10; i++) {
    id += VOYA_ID_ALPHABET[bytes[i]! % VOYA_ID_ALPHABET.length];
  }
  return `VOYA-${id}`;
}
