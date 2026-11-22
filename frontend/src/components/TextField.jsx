import { useId } from "react";

// Labelled input, 32px like the buttons. Errors turn the border red and show 12px text below (NFR-34).
export default function TextField({
  label,
  error,
  className = "",
  ...inputProps
}) {
  const id = useId();
  const messages = Array.isArray(error) ? error : error ? [error] : [];
  const errorId = messages.length > 0 ? `${id}-error` : undefined;
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-[13px] font-medium">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={messages.length > 0 || undefined}
        aria-describedby={errorId}
        className={`text-brown-900 focus:border-brown-900 h-8 rounded-md border bg-white px-3 text-sm outline-none ${
          messages.length > 0 ? "border-error" : "border-cream-300"
        }`}
        {...inputProps}
      />
      {errorId && (
        <p id={errorId} className="text-error text-xs">
          {messages.join(" ")}
        </p>
      )}
    </div>
  );
}
