const won = new Intl.NumberFormat("ko-KR");

// The only money formatter in the app (NFR-33): 29000 -> "29,000원".
export function formatWon(amount) {
  return `${won.format(amount)}원`;
}
