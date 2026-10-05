export function isRecord(value: unknown): value is Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}
export function record(value: unknown, name: string): asserts value is Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`${name} must be a plain object.`);
}
export function textField(value: unknown, name: string, empty = false): asserts value is string {
  if (typeof value !== 'string' || (!empty && !value.trim())) throw new Error(`${name} must be ${empty ? 'a' : 'a nonempty'} string.`);
}
export function identifier(value: unknown): asserts value is string {
  if (typeof value !== 'string' || !/^[A-Za-z][A-Za-z0-9_.:-]{0,159}$/.test(value)
    || Object.getOwnPropertyNames(Object.prototype).includes(value) || value === 'prototype') throw new Error('IDs must be safe, unique identifiers (1–160 characters).');
}
export function identifiers(value: unknown, name: string, unique = false): asserts value is string[] {
  if (!Array.isArray(value)) throw new Error(`${name} must be an array of identifiers.`);
  for (const id of value) identifier(id);
  if (unique && new Set(value).size !== value.length) throw new Error(`${name} must be unique.`);
}
export function jsonValue(value: unknown, depth = 0): boolean {
  if (depth > 30) return false;
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return true;
  if (typeof value === 'number') return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(v => jsonValue(v, depth + 1));
  return isRecord(value) && Object.values(value).every(v => jsonValue(v, depth + 1));
}
