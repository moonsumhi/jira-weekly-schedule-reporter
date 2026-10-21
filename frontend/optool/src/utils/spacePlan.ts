/** Internal deployments use HTTP. getRandomValues also works outside secure contexts. */
export function newSpaceId(): string {
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

/** Include rotated corners so fitting the view never clips a wall or desk. */
export function drawingBounds(
  objects: { x: number; y: number; width: number; height: number; rotation: number }[],
) {
  if (!objects.length) return null;
  const points = objects.flatMap((object) => {
    const angle = (object.rotation * Math.PI) / 180;
    return [
      [0, 0],
      [object.width, 0],
      [0, object.height],
      [object.width, object.height],
    ].map(([x = 0, y = 0]) => ({
      x: object.x + x * Math.cos(angle) - y * Math.sin(angle),
      y: object.y + x * Math.sin(angle) + y * Math.cos(angle),
    }));
  });
  const left = Math.min(...points.map((p) => p.x)),
    right = Math.max(...points.map((p) => p.x));
  const top = Math.min(...points.map((p) => p.y)),
    bottom = Math.max(...points.map((p) => p.y));
  const width = Math.max(600, right - left + 160),
    height = Math.max(400, bottom - top + 160);
  return { x: (left + right - width) / 2, y: (top + bottom - height) / 2, width, height };
}
