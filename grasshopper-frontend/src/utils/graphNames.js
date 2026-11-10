// scans are named by capture time, e.g. 2025-06-01T08-12-00.ttl
export const TIMESTAMP_GRAPH = /^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.ttl$/

export function isTimestampGraph(name) {
  return TIMESTAMP_GRAPH.test(name)
}

export function isCompareGraph(name) {
  return name.includes('_vs_')
}

export function stem(name) {
  return name.replace(/\.gz$/, '').replace(/\.ttl$/, '')
}

// '2026-10-13T20-51-44.ttl' -> '20:51:44'
export function graphTime(ttlName) {
  return ttlName.slice(11, 19).replaceAll('-', ':')
}

// '2026-10-02T09-15-00.ttl' -> '2026-10-02 09:15'; other names (base.ttl) keep their stem
export function graphLabel(name) {
  const file = name.endsWith('.ttl') ? name : `${name}.ttl`
  if (!isTimestampGraph(file)) return stem(name)
  return `${file.slice(0, 10)} ${graphTime(file).slice(0, 5)}`
}

// '<ts1>_vs_<ts2>.ttl' -> ['2026-10-02 09:15', '2026-10-06 11:00']
export function compareLabel(name) {
  const [first, second = ''] = stem(name).split('_vs_')
  return [graphLabel(first), second ? graphLabel(second) : '']
}

export function monthOf(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

// timestamped graphs grouped by day: { 'YYYY-MM-DD': [{ ttl_name }] }
export function groupByDay(names) {
  const days = {}
  for (const name of names) {
    if (!isTimestampGraph(name)) continue
    const day = name.slice(0, 10)
    ;(days[day] ||= []).push({ ttl_name: name })
  }
  for (const graphs of Object.values(days)) {
    graphs.sort((a, b) => a.ttl_name.localeCompare(b.ttl_name))
  }
  return days
}

// sorted 'YYYY-MM' months that have timestamped graphs
export function monthsWithGraphs(names) {
  return [
    ...new Set(names.filter(isTimestampGraph).map(name => name.slice(0, 7))),
  ].sort()
}
