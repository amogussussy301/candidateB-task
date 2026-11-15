export type WorkStatus = "planned" | "done" | "cancelled";

export interface WorkReport {
  work_id: string;
  title: string;
  status: WorkStatus;
  price: string;
  paid: string;
  remaining: string;
}

export interface ContractReport {
  contract_id: string;
  contractor: string;
  contract_amount: string;
  active_works_amount: string;
  paid: string;
  remaining: string;
  unallocated: string;
  paid_percent: number;
  works: WorkReport[];
}

export interface ReportTotals {
  contract_amount: string;
  active_works_amount: string;
  paid: string;
  remaining: string;
  unallocated: string;
}

export interface Report {
  report_date: string;
  contracts: ContractReport[];
  totals: ReportTotals;
}

export async function fetchReport(reportDate: string, signal?: AbortSignal): Promise<Report> {
  const query = new URLSearchParams({ report_date: reportDate });
  let response: Response;
  try {
    response = await fetch(`/api/report?${query}`, {
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }
    throw new Error("Не удалось связаться с сервером. Проверьте подключение и повторите попытку.");
  }

  if (!response.ok) {
    const message =
      response.status === 422
        ? "Проверьте дату отчёта и попробуйте ещё раз."
        : "Не удалось получить отчёт. Проверьте, что сервер запущен.";
    throw new Error(message);
  }
  return (await response.json()) as Report;
}
