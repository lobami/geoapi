export function compactNumber(value) {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value ?? 0)
}

export function percent(value) {
  return `${Math.round((value ?? 0) * 100)}%`
}

export function niceDate(value) {
  if (!value) return 'No date'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value))
}
