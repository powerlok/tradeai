export function formatPrice(value: number) {
  return value.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
}

export function formatMetric(value: number | null | undefined) {
  return value == null ? '--' : value.toLocaleString('pt-BR', { maximumFractionDigits: 4 });
}

export function parseToken(token: string) {
  try {
    return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return null;
  }
}
