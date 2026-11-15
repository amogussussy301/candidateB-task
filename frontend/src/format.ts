export function formatMoney(value: string): string {
  const match = /^(-?)(\d+)\.(\d{2})$/.exec(value);
  if (!match) {
    throw new Error(`Некорректная денежная сумма: ${value}`);
  }

  const [, sign, rubles, kopecks] = match;
  const grouped = rubles.replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
  return `${sign ? "−" : ""}${grouped},${kopecks}\u00a0₽`;
}

export function formatDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(year, month - 1, day));
}
