import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Report } from "./api";

const reportFixture: Report = {
  report_date: "2026-11-10",
  totals: {
    contract_amount: "690000.00",
    active_works_amount: "590000.00",
    paid: "390000.00",
    remaining: "200000.00",
    unallocated: "0.00",
  },
  contracts: [
    {
      contract_id: "D-1",
      contractor: "Студия «Свет»",
      contract_amount: "600000.00",
      active_works_amount: "500000.00",
      paid: "315000.00",
      remaining: "185000.00",
      unallocated: "0.00",
      paid_percent: 63,
      works: [
        {
          work_id: "W-13",
          title: "Съёмка: аксессуары",
          status: "cancelled",
          price: "100000.00",
          paid: "0.00",
          remaining: "0.00",
        },
        {
          work_id: "W-15",
          title: "Съёмка: зима",
          status: "planned",
          price: "100000.00",
          paid: "15000.00",
          remaining: "85000.00",
        },
      ],
    },
    {
      contract_id: "D-2",
      contractor: "Иван Петров, дизайнер",
      contract_amount: "90000.00",
      active_works_amount: "90000.00",
      paid: "75000.00",
      remaining: "15000.00",
      unallocated: "0.00",
      paid_percent: 83,
      works: [
        {
          work_id: "W-23",
          title: "Упаковка",
          status: "planned",
          price: "40000.00",
          paid: "25000.00",
          remaining: "15000.00",
        },
      ],
    },
  ],
};

function responseWith(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const fetchMock = vi.fn<typeof fetch>();

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders contracts, exact amounts and work statuses from the API", async () => {
    fetchMock.mockResolvedValueOnce(responseWith(reportFixture));
    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("Формируем отчёт");
    const contract = await screen.findByRole("article", { name: "Студия «Свет»" });
    expect(within(contract).getByText(/315\s000,00\s₽/)).toBeInTheDocument();
    expect(within(contract).getByText("Съёмка: аксессуары")).toBeInTheDocument();
    expect(within(contract).getByText("Отменена")).toBeInTheDocument();
    expect(within(contract).getByText("Не входит в активный итог")).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Иван Петров, дизайнер" })).toBeInTheDocument();
    expect(screen.getByText("Упаковка")).toBeInTheDocument();
    expect(screen.getAllByText("Запланирована")).toHaveLength(2);
  });

  it("requests and displays a newly selected report date", async () => {
    const user = userEvent.setup();
    fetchMock
      .mockResolvedValueOnce(responseWith(reportFixture))
      .mockResolvedValueOnce(responseWith({ ...reportFixture, report_date: "2026-11-12" }));
    render(<App />);
    await screen.findByRole("article", { name: "Студия «Свет»" });

    fireEvent.change(screen.getByLabelText("Отчёт на дату"), {
      target: { value: "2026-11-12" },
    });
    await user.click(screen.getByRole("button", { name: "Обновить" }));

    await screen.findByText(/на 12 ноября 2026/);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/report?report_date=2026-11-12");
  });

  it("shows a validation error and recovers with retry", async () => {
    const user = userEvent.setup();
    fetchMock
      .mockResolvedValueOnce(responseWith({ detail: "Invalid date" }, 422))
      .mockResolvedValueOnce(responseWith(reportFixture));
    render(<App />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Проверьте дату отчёта");
    await user.click(screen.getByRole("button", { name: "Попробовать снова" }));
    expect(await screen.findByRole("article", { name: "Студия «Свет»" })).toBeInTheDocument();
  });

  it("explains a network failure", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось связаться с сервером");
  });

  it("shows an empty state when there are no contracts", async () => {
    fetchMock.mockResolvedValueOnce(responseWith({ ...reportFixture, contracts: [] }));
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Договоры не найдены" })).toBeInTheDocument();
    expect(screen.getByText("Проверьте исходные файлы в папке data.")).toBeInTheDocument();
  });
});
