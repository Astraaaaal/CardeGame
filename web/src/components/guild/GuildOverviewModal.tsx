import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { guildsApi } from "@/api/guilds";
import Modal from "@/components/ui/Modal";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmojiText from "@/components/ui/EmojiText";
import { formatNumber } from "@/utils/format";
import GuildEmblem, { POLICY_LABEL, ROLE_LABEL } from "./GuildEmblem";

/** Fiche d'une guilde vue de l'extérieur : niveau, puissance, membres ; `action` = bouton rejoindre éventuel. */
export default function GuildOverviewModal({ guildId, onClose, action }: {
    guildId: number | null;
    onClose: () => void;
    action?: React.ReactNode;
}) {
    const navigate = useNavigate();
    const { data, isLoading } = useQuery({
        queryKey: ["guild", "public", guildId], queryFn: () => guildsApi.get(guildId!), enabled: guildId != null,
    });
    const progress = data && data.xp_next_level > data.xp_current_level
        ? (data.xp - data.xp_current_level) / (data.xp_next_level - data.xp_current_level) : 0;

    return (
        <Modal open={guildId != null} onClose={onClose} title={data ? `[${data.tag}] ${data.name}` : "Guilde"}>
            {isLoading || !data ? <LoadingSpinner text="Chargement..." /> : (
                <div className="space-y-3">
                    <div className="flex items-center gap-3">
                        <GuildEmblem icon={data.icon} color={data.color} size={52} />
                        <div className="flex-1 min-w-0 text-sm">
                            <p className="text-white font-semibold">Niveau {data.level}</p>
                            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden my-1">
                                <div className="h-full bg-accent" style={{ width: `${Math.round(progress * 100)}%` }} />
                            </div>
                            <p className="text-white/50 text-[11px]">
                                {data.members}/{data.max_members} membres · puissance {formatNumber(data.power)} · {POLICY_LABEL[data.join_policy]}
                            </p>
                        </div>
                    </div>
                    {data.welcome_message && (
                        <p className="text-white/70 text-sm bg-black/20 rounded-lg px-3 py-2 whitespace-pre-line">
                            <EmojiText text={data.welcome_message} />
                        </p>
                    )}
                    <p className="text-white/40 text-[11px]">Meilleur palier de défi : {data.challenge_best_tier}</p>
                    <div className="space-y-1 max-h-64 overflow-y-auto">
                        {data.members_list.map((m) => (
                            <button key={m.user_id} className="w-full flex items-center gap-2 text-left bg-black/20 rounded-lg px-3 py-1.5 hover:bg-white/5"
                                onClick={() => { onClose(); navigate(`/players/${m.user_id}`); }}>
                                <span className="flex-1 min-w-0 truncate text-white text-sm">{m.display_name}</span>
                                <span className="text-white/40 text-[11px]">{ROLE_LABEL[m.role]}</span>
                                <span className="text-gold text-[11px] font-semibold tabular-nums w-16 text-right">{formatNumber(m.power)}</span>
                            </button>
                        ))}
                    </div>
                    {action}
                </div>
            )}
        </Modal>
    );
}
