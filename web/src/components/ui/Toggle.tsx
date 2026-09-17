/** Interrupteur on/off. */
export default function Toggle({ checked, onChange, disabled = false }: {
    checked: boolean;
    onChange: (v: boolean) => void;
    disabled?: boolean;
}) {
    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
            disabled={disabled}
            className={`w-11 h-6 p-0 rounded-full transition-colors relative shrink-0 disabled:opacity-40 ${checked ? "bg-accent" : "bg-white/15"}`}
            onClick={() => onChange(!checked)}
        >
            <span
                className={`absolute left-0.5 top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                    checked ? "translate-x-5" : "translate-x-0"
                }`}
            />
        </button>
    );
}
