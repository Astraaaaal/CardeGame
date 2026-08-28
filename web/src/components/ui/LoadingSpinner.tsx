interface LoadingSpinnerProps {
    size?: "sm" | "md" | "lg";
    text?: string;
}

const sizeMap = { sm: "h-6 w-6", md: "h-10 w-10", lg: "h-16 w-16" };

export default function LoadingSpinner({
    size = "md",
    text,
}: LoadingSpinnerProps) {
    return (
        <div className="flex flex-col items-center justify-center gap-3 py-12">
            <svg
                className={`animate-spin text-accent ${sizeMap[size]}`}
                viewBox="0 0 24 24"
            >
                <circle
                    className="opacity-25"
                    cx="12" cy="12" r="10"
                    stroke="currentColor" strokeWidth="4" fill="none"
                />
                <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
            </svg>
            {text && <p className="text-white/60 text-sm">{text}</p>}
        </div>
    );
}
