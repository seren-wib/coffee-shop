import {
  ORDER_STATUS,
  PAYMENT_STATUS,
  SALES_STATUS,
  label,
} from "../lib/labels";

// Espresso badge; the state is told by the text and the dot color (components sheet).
const TYPES = {
  order: {
    names: ORDER_STATUS,
    dots: {
      PENDING: "bg-brown-400",
      PAID: "bg-dot-green",
      PREPARING: "bg-amber-400",
      SHIPPED: "bg-dot-blue",
      DELIVERED: "bg-latte-100",
      CANCEL_REQUESTED: "bg-dot-orange",
      CANCELLED: "bg-dot-red",
    },
  },
  sales: {
    names: SALES_STATUS,
    dots: {
      ON_SALE: "bg-dot-green",
      SOLD_OUT: "bg-dot-red",
      STOPPED: "bg-brown-400",
    },
  },
  payment: {
    names: PAYMENT_STATUS,
    dots: {
      READY: "bg-brown-400",
      SUCCESS: "bg-dot-green",
      FAILED: "bg-dot-red",
      CANCELLED: "bg-dot-red",
    },
  },
};

const SIZES = {
  md: "px-2.5 py-1 text-[13px]",
  sm: "px-2 py-[3px] text-xs",
};

export default function StatusBadge({
  status,
  type = "order",
  size = "md",
  className = "",
}) {
  const { names, dots } = TYPES[type];
  return (
    <span
      className={`bg-espresso-950 text-latte-100 inline-flex items-center gap-1.5 rounded-sm font-medium ${SIZES[size]} ${className}`}
    >
      <span
        aria-hidden="true"
        className={`size-1.5 rounded-[1px] ${dots[status] ?? "bg-brown-400"}`}
      />
      {label(names, status)}
    </span>
  );
}
