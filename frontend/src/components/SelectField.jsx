import { useId } from "react";

// Labelled select, 32px like the inputs. options: [{value, label}].
export default function SelectField({
  label,
  options,
  className = "",
  ...selectProps
}) {
  const id = useId();
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-[13px] font-medium">
        {label}
      </label>
      <select
        id={id}
        className="border-cream-300 text-brown-900 focus:border-brown-900 h-8 rounded-md border bg-white px-2.5 text-sm outline-none"
        {...selectProps}
      >
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
          >
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
