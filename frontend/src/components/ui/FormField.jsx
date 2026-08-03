/**
 * FormField Component
 * ====================
 * Reusable form field with label, input, and error display.
 */

export default function FormField({
  label,
  name,
  type = "text",
  value,
  onChange,
  placeholder,
  required = false,
  error,
  disabled = false,
  children, // For select/textarea overrides
}) {
  const inputClasses =
    "w-full px-4 py-2.5 bg-gray-800/50 border rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 transition-all disabled:opacity-50 disabled:cursor-not-allowed " +
    (error
      ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/20"
      : "border-gray-700/50 focus:border-violet-500/50 focus:ring-violet-500/20");

  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-300">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
      )}

      {children ? (
        children
      ) : type === "textarea" ? (
        <textarea
          id={name}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          rows={3}
          className={inputClasses + " resize-none"}
        />
      ) : (
        <input
          id={name}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          className={inputClasses}
        />
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
