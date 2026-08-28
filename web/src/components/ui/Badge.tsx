interface BadgeProps {
    label: string;
    color?: string;
    className?: string;
}

export default function Badge({ label, color, className = "" }: BadgeProps) {
    return (
        <span
            className={`
        inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold
        uppercase tracking-wider ${className}
      `}
            style={color ? { backgroundColor: color, color: "#fff" } : undefined}
        >
            {label}
        </span>
    );
}
