/**
 * Resolve Strapi Media Library URLs to absolute browser URLs (Strapi v4/v5 shapes).
 */

export function absoluteMediaUrl(url: string, strapiBaseUrl: string): string {
  if (!url) return url;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const base = strapiBaseUrl.replace(/\/?$/, '');
  const path = url.startsWith('/') ? url : `/${url}`;
  return `${base}${path}`;
}

/**
 * Extract a single media URL from Strapi REST payloads (`data.attributes.url`, flat `url`, etc.).
 */
export function pickMediaUrl(media: unknown, strapiBaseUrl: string): string | undefined {
  if (media == null || typeof media !== 'object') return undefined;

  const visit = (node: unknown): string | undefined => {
    if (node == null || typeof node !== 'object') return undefined;
    const n = node as Record<string, unknown>;

    if (Array.isArray(node)) {
      for (const item of node) {
        const u = visit(item);
        if (u) return u;
      }
      return undefined;
    }

    if ('data' in n) {
      const data = n.data;
      if (data == null) return undefined;
      if (Array.isArray(data)) {
        for (const item of data) {
          const u = visit(item);
          if (u) return u;
        }
        return undefined;
      }
      return visit(data);
    }

    if (typeof n.url === 'string' && n.url.length > 0) {
      return absoluteMediaUrl(n.url, strapiBaseUrl);
    }

    if (n.attributes && typeof n.attributes === 'object') {
      const attrs = n.attributes as Record<string, unknown>;
      if (typeof attrs.url === 'string' && attrs.url.length > 0) {
        return absoluteMediaUrl(attrs.url, strapiBaseUrl);
      }
    }

    return undefined;
  };

  return visit(media);
}
