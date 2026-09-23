import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { guildsApi } from "@/api/guilds";
import SocialButton from "@/components/layout/SocialButton";
import NoGuild, { MY_GUILD_KEY } from "@/components/guild/NoGuild";
import GuildView from "@/components/guild/GuildView";

/** Guilde du joueur, ou création / recherche s'il n'en a pas. */
export default function Guild() {
    const navigate = useNavigate();
    // Rafraîchi régulièrement : progression du défi, nouveaux membres, bonus.
    const { data, isLoading } = useQuery({ queryKey: MY_GUILD_KEY, queryFn: guildsApi.me, refetchInterval: 30_000 });

    return (
        <div className="min-h-screen bg-game-bg flex flex-col pb-14 desktop:pb-0">
            <header className="relative flex items-center justify-between pl-4 pr-14 py-3 bg-game-surface/50 border-b border-white/5">
                <button className="text-accent text-sm font-semibold" onClick={() => navigate("/")}>
                    Retour
                </button>
                <h1 className="absolute left-1/2 -translate-x-1/2 max-w-[55%] truncate text-white font-bold pointer-events-none">Guilde</h1>
                <span className="w-14" />
            </header>

            <main className="flex-1 px-4 py-6 max-w-sm mx-auto w-full pb-24">
                {isLoading && <p className="text-white/40 text-sm text-center">Chargement...</p>}
                {data && (data.guild ? <GuildView guild={data.guild} /> : <NoGuild state={data} />)}
            </main>

            <SocialButton />
        </div>
    );
}
