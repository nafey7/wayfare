/**
 * Convert snake_case to camelCase
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
}

/**
 * Convert camelCase to snake_case
 */
export function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

/**
 * Recursively transform object keys from snake_case to camelCase
 */
export function toCamelCase<T>(obj: T): T {
  if (Array.isArray(obj)) {
    return obj.map(toCamelCase) as T;
  }

  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    return Object.keys(obj).reduce(
      (acc, key) => {
        // MongoDB _id → id (convention); snakeToCamel('_id') would give 'Id'
        const camelKey =
          key === '_id' ? 'id' : snakeToCamel(key);
        (acc as Record<string, unknown>)[camelKey] = toCamelCase(
          (obj as Record<string, unknown>)[key]
        );
        return acc;
      },
      {} as Record<string, unknown>
    ) as T;
  }

  return obj;
}

/**
 * Recursively transform object keys from camelCase to snake_case
 */
export function toSnakeCase<T>(obj: T): T {
  if (Array.isArray(obj)) {
    return obj.map(toSnakeCase) as T;
  }

  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    return Object.keys(obj).reduce(
      (acc, key) => {
        const snakeKey = camelToSnake(key);
        (acc as Record<string, unknown>)[snakeKey] = toSnakeCase(
          (obj as Record<string, unknown>)[key]
        );
        return acc;
      },
      {} as Record<string, unknown>
    ) as T;
  }

  return obj;
}
