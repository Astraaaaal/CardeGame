import api from "./client";

export interface BugReportCreate {
    subject: string;
    body: string;
    page_context?: string;
}

export interface BugReportOut {
    id: number;
    username: string;
    subject: string;
    body: string;
    page_context: string | null;
    created_at: string;
    resolved_at: string | null;
}

export const supportApi = {
    submitBugReport: (data: BugReportCreate) =>
        api.post<BugReportOut>("/support/bug-reports", data).then((r) => r.data),
};
