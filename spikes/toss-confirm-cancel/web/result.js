// Show every query parameter Toss appended, plus when the page was reached.
// The confirm call is made from toss.py, not from here, so the secret key
// never touches the browser.
const params = Object.fromEntries(new URLSearchParams(location.search));
const requestedAt = params.orderId
  ? localStorage.getItem(`requestedAt:${params.orderId}`)
  : null;
document.getElementById("result").textContent = JSON.stringify(
  {
    page: location.pathname,
    paramNames: Object.keys(params),
    params,
    requestedAt,
    returnedAt: new Date().toISOString(),
  },
  null,
  2,
);
