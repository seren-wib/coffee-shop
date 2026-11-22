// Buttons from the components sheet: 32px high (sm 28px), 6px corners, 14/500.
// One primary per screen; irreversible actions use danger plus a confirm dialog.
const VARIANTS = {
  primary: "border-transparent bg-caramel-700 text-white hover:bg-caramel-800",
  outline:
    "border-caramel-700 bg-transparent text-caramel-700 hover:bg-cream-100",
  secondary: "border-cream-300 bg-white text-brown-900 hover:bg-cream-100",
  ghost:
    "border-transparent bg-transparent text-brown-900 underline underline-offset-4",
  danger: "border-error bg-transparent text-error hover:bg-cream-100",
};

const SIZES = {
  md: "h-8 px-3 text-sm",
  sm: "h-7 px-2.5 text-[13px]",
};

export default function Button({
  variant = "primary",
  size = "md",
  type = "button",
  className = "",
  ...props
}) {
  return (
    <button
      type={type}
      className={`disabled:bg-cream-300 disabled:text-brown-600 inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-md border font-medium whitespace-nowrap disabled:cursor-not-allowed disabled:border-transparent disabled:no-underline ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    />
  );
}
