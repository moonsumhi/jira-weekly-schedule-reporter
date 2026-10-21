import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { webcrypto } from 'node:crypto';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/spacePlan.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { newSpaceId, drawingBounds } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
);

test('object and seat IDs work on internal HTTP without crypto.randomUUID', () => {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  Object.defineProperty(globalThis, 'crypto', {
    configurable: true,
    value: { getRandomValues: (value) => webcrypto.getRandomValues(value) },
  });
  try {
    const ids = Array.from({ length: 1000 }, () => newSpaceId());
    assert.equal(new Set(ids).size, ids.length);
    for (const id of ids) assert.match(id, /^[a-f0-9]{32}$/);
  } finally {
    if (descriptor) Object.defineProperty(globalThis, 'crypto', descriptor);
    else delete globalThis.crypto;
  }
});

test('view fitting handles an empty canvas and keeps a single desk at a usable scale', () => {
  assert.equal(drawingBounds([]), null);
  const box = drawingBounds([{ x: 500, y: 300, width: 100, height: 60, rotation: 0 }]);
  assert.ok(box.width >= 600 && box.height >= 400);
  assert.equal(box.x + box.width / 2, 550);
  assert.equal(box.y + box.height / 2, 330);
});

test('view fitting includes rotated walls and distant objects without changing the plan', () => {
  const objects = [
    { x: 0, y: 0, width: 1200, height: 10, rotation: 90 },
    { x: 1800, y: -200, width: 100, height: 60, rotation: 180 },
  ];
  const before = structuredClone(objects);
  const box = drawingBounds(objects);
  for (const [x, y] of [
    [-10, 1200],
    [0, 0],
    [1800, -200],
    [1700, -260],
  ]) {
    assert.ok(x >= box.x && x <= box.x + box.width);
    assert.ok(y >= box.y && y <= box.y + box.height);
  }
  assert.deepEqual(objects, before);
});
