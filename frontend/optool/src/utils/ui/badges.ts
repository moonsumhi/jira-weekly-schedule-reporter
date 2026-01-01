import type { AssetAction } from 'src/types/assets'

export function historyBadgeColor(a: AssetAction): string {
  if (a === 'CREATE') return 'positive'
  if (a === 'DELETE') return 'negative'
  return 'primary'
}
