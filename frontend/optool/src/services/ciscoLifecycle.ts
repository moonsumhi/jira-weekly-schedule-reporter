/** ACI-mode software only; never reinterpret standalone NX-OS versions. */
export function normalizeCiscoSoftware(product: string, version: string): { dist: string; version: string } | null {
  const names: Record<string, string> = { apic: 'Cisco APIC', ciscoapic: 'Cisco APIC', aciswitch: 'Cisco ACI Switch', ciscoaciswitch: 'Cisco ACI Switch' }
  const dist = names[product.toLowerCase().replace(/[\s_-]/g, '')]
  if (!dist) return null
  const match = version.trim().match(/^(\d+\.\d+)(?:\(\d+[a-z]?\)|\.\d+[a-z]?)?$/i)
  return { dist, version: match?.[1] ?? version.trim() }
}
