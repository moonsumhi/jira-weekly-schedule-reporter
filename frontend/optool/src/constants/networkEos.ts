import audit from 'src/data/lifecycle_audit.json'

// Canonical source: app/data/lifecycle_audit.json. Build validates the mirror.
export const NETWORK_EOS_LIST = [...audit.network, ...audit.additionalNetwork]
