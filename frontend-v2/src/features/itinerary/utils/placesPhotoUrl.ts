/** Map authenticated Places proxy URLs to the public session endpoint. */
export function toPublicPlacesPhotoUrl(src: string): string {
  if (src.includes('/api/public/places/photos/')) {
    return src;
  }
  return src.replace('/api/places/photos/', '/api/public/places/photos/');
}
