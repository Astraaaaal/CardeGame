import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AccountEditor from "@/components/profile/AccountEditor";
import SupportPanel from "@/components/profile/SupportPanel";
import SettingsEditor from "@/components/profile/SettingsEditor";

type Tab = "profile" | "support" | "settings";

export default function Settings() {
    const navigate = useNavigate();
    const [tab, setTab] = useState<Tab>("profile");

    return (
        <div className="min-h-screen bg-game-bg flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    ← Retour
                </button>
                <h1 className="text-white font-bold">⚙️ Réglages</h1>
                <span className="w-14" />
            </header>

            <div className="flex border-b border-white/5">
                {([
                    { key: "profile", label: "Profil" },
                    { key: "support", label: "Support" },
                    { key: "settings", label: "Paramètres" },
                ] as const).map((t) => (
                    <button
                        key={t.key}
                        className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
                            tab === t.key ? "text-accent border-b-2 border-accent" : "text-white/40 hover:text-white/70"
                        }`}
                        onClick={() => setTab(t.key)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full">
                {tab === "profile" && <AccountEditor />}
                {tab === "support" && <SupportPanel />}
                {tab === "settings" && <SettingsEditor />}
            </main>
        </div>
    );
}
