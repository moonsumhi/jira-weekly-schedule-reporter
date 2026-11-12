import type { CardSize } from 'src/services/prefs'

export function resolveDashboardLayout(savedOrder: string[], savedSizes: Record<string, CardSize>, baseOrder: string[]) {
  const kept = [...new Set(savedOrder.filter(id => baseOrder.includes(id)))]
  const order = [...kept, ...baseOrder.filter(id => !kept.includes(id))]
  // Apply the requested arrangement once when retiring D-Day / introducing
  // movable shortcuts. Later user arrangements and custom sizes stay intact.
  const needsNewArrangement = savedOrder.includes('dday') || !savedOrder.includes('calendar')
    || (baseOrder.includes('favorites') && !savedOrder.includes('favorites'))
  return { order: needsNewArrangement ? [...baseOrder] : order, sizes: { ...savedSizes } }
}
