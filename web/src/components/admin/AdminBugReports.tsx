import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminBugReportsApi } from "@/api/admin";
import Button from "@/components/ui/Button";

function fmt(iso: string): string {
    return new Date(iso).toLocaleDateString("fr-FR", {
        day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
}

export default function AdminBugReports() {
    const qc = useQueryClient();
    const { data, isLoading } = useQuery({ queryKey: ["admin", "bug-reports"], queryFn: adminBugReportsApi.list });

    const resolve = useMutation({
        mutationFn: (id: number) => adminBugReportsApi.resolve(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "bug-reports"] }),
    });
    const remove = useMutation({
        mutationFn: (id: number) => adminBugReportsApi.remove(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "bug-reports"] }),
    });

    if (isLoading) return <p className="text-white/40 text-sm">…</p>;

    const reports = data ?? [];
    if (reports.length === 0) {
        return <p className="text-white/40 text-sm text-center py-8">Aucun signalement.</p>;
    }

    return (
        <div className="space-y-2">
            {reports.map((r) => (
                <div
                    key={r.id}
                    className={`bg-game-surface/60 border rounded-lg p-3 space-y-1.5 ${
                        r.resolved_at ? "border-white/5 opacity-50" : "border-white/10"
                    }`}
                >
                    <div className="flex items-center justify-between gap-2">
                        <p className="text-white text-sm font-semibold truncate">{r.subject}</p>
                        {r.resolved_at && <span className="text-green-400 text-[10px] shrink-0">✓ Résolu</span>}
                    </div>
                    <p className="text-white/40 text-xs">
                        {r.username} · {fmt(r.created_at)} {r.page_context && `· ${r.page_context}`}
                    </p>
                    <p className="text-white/70 text-xs whitespace-pre-wrap">{r.body}</p>
                    <div className="flex gap-2 pt-1">
                        {!r.resolved_at && (
                            <Button
                                variant="secondary" size="sm"
                                loading={resolve.isPending}
                                onClick={() => resolve.mutate(r.id)}
                            >
                                Marquer résolu
                            </Button>
                        )}
                        <button
                            className="text-red-400/70 hover:text-red-400 text-xs px-2"
                            onClick={() => remove.mutate(r.id)}
                        >
                            Supprimer
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
