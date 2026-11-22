// −/+ quantity box, 32px. + stops at max (the option's stock, DR-10); the server checks again.
export default function QuantityStepper({
  value,
  onChange,
  min = 1,
  max = Infinity,
  disabled = false,
  label = "수량",
  testId,
}) {
  const button =
    "h-[30px] w-8 cursor-pointer text-base text-brown-900 disabled:cursor-not-allowed disabled:text-brown-400";
  return (
    <div
      role="group"
      aria-label={label}
      className="border-cream-300 flex h-8 w-28 items-center rounded-md border bg-white"
    >
      <button
        type="button"
        aria-label="수량 빼기"
        className={button}
        disabled={disabled || value <= min}
        onClick={() => onChange(value - 1)}
      >
        −
      </button>
      <span data-testid={testId} className="grow text-center text-sm">
        {value}
      </span>
      <button
        type="button"
        aria-label="수량 더하기"
        className={button}
        disabled={disabled || value >= max}
        onClick={() => onChange(value + 1)}
      >
        +
      </button>
    </div>
  );
}
