/**
 * Standard option shape for profile preference controls.
 * id: Stable key for React (unique within the options list)
 * label: Display text
 * value: Stored value (sent to API / used in state)
 */
export interface PreferenceOption<T = string> {
  id: string;
  label: string;
  value: T;
}
