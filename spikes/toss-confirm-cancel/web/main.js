import { ANONYMOUS, loadTossPayments } from "@tosspayments/tosspayments-sdk";

const out = document.getElementById("out");

document.getElementById("pay").addEventListener("click", async () => {
  const label = document.getElementById("label").value.trim() || "X";
  const amount = Number(document.getElementById("amount").value);
  // Same shape as SDD 4.6.1 pg_order_id: <order id>-P<n>
  const stamp = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  const orderId = `SPIKE-${stamp}-${label}-P1`;
  const requestedAt = new Date().toISOString();
  localStorage.setItem(`requestedAt:${orderId}`, requestedAt);
  out.textContent = JSON.stringify({ orderId, amount, requestedAt }, null, 2);
  try {
    const toss = await loadTossPayments(__TOSS_CLIENT_KEY__);
    const payment = toss.payment({ customerKey: ANONYMOUS });
    await payment.requestPayment({
      method: "CARD",
      amount: { currency: "KRW", value: amount },
      orderId,
      orderName: `Spike Blend ${label}`,
      successUrl: `${location.origin}/success.html`,
      failUrl: `${location.origin}/fail.html`,
    });
  } catch (e) {
    // Window closed or SDK error before redirect.
    out.textContent += `\nrequestPayment threw: ${JSON.stringify({ code: e.code, message: e.message })}`;
  }
});
