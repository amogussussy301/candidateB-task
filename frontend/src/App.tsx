import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { fetchReport, type Report } from "./api";
import { ContractCard } from "./components/ContractCard";
import { formatDate, formatMoney } from "./format";

const DEFAULT_DATE = "2026-11-10";

interface SummaryCardProps {
  label: string;
  value: string;
  hint: string;
  tone?: "paid" | "remaining";
}

function SummaryCard({ label, value, hint, tone }: SummaryCardProps) {
  return (
    <article className={`summary-card${tone ? ` summary-card-${tone}` : ""}`}>
      <p>{label}</p>
      <strong>{formatMoney(value)}</strong>
      <span>{hint}</span>
    </article>
  );
}

function LoadingState() {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="sr-only">Формируем отчёт</span>
      <div className="skeleton skeleton-title" />
      <div className="skeleton-grid">
        {[0, 1, 2, 3].map((item) => (
          <div className="skeleton skeleton-card" key={item} />
        ))}
      </div>
      <div className="skeleton skeleton-contract" />
      <p>Формируем отчёт…</p>
    </div>
  );
}

function PageShell({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="topbar">
        <a className="brand" href="/" aria-label="Авансы по договорам — на главную">
          <span className="brand-mark" aria-hidden="true">А</span>
          <span className="brand-copy">
            <strong>Авансы</strong>
            <small>учёт подрядчиков</small>
          </span>
        </a>
        <div className="topbar-status">
          <span aria-hidden="true" />
          Данные из учёта
        </div>
      </header>
      {children}
    </>
  );
}

export default function App() {
  const [draftDate, setDraftDate] = useState(DEFAULT_DATE);
  const [reportDate, setReportDate] = useState(DEFAULT_DATE);
  const [reloadKey, setReloadKey] = useState(0);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    fetchReport(reportDate, controller.signal)
      .then(setReport)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Не удалось сформировать отчёт.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [reportDate, reloadKey]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (draftDate === reportDate) {
      setReloadKey((key) => key + 1);
    } else {
      setReportDate(draftDate);
    }
  }

  const dateForm = (
    <form className="date-form" onSubmit={handleSubmit}>
      <div className="date-form-heading">
        <span className="calendar-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <rect x="3" y="5" width="18" height="16" rx="3" />
            <path d="M7 3v4M17 3v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01" />
          </svg>
        </span>
        <div>
          <label htmlFor="report-date">Отчёт на дату</label>
          <p>Платежи — по фактической дате</p>
        </div>
      </div>
      <div className="date-form-controls">
        <input
          id="report-date"
          type="date"
          value={draftDate}
          onChange={(event) => setDraftDate(event.target.value)}
          required
        />
        <button type="submit" disabled={loading}>
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M20 6v5h-5M4 18v-5h5" />
            <path d="M18.2 9A7 7 0 0 0 6.1 6.1L4 8m2 7a7 7 0 0 0 11.9 2.9L20 16" />
          </svg>
          {loading ? "Считаем…" : "Обновить"}
        </button>
      </div>
    </form>
  );

  return (
    <PageShell>
      <main className="page-content" aria-busy={loading}>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Финансовый обзор</p>
            <h1>Авансы по договорам</h1>
            <p className="hero-description">
              Сколько уже выплачено по каждой работе<br className="desktop-break" /> и сколько осталось оплатить.
            </p>
          </div>
          {dateForm}
        </section>

        {loading && <LoadingState />}

        {!loading && error && (
          <section className="error-state" role="alert">
            <div className="error-icon" aria-hidden="true">!</div>
            <div>
              <h2>Отчёт не загрузился</h2>
              <p>{error}</p>
            </div>
            <button type="button" onClick={() => setReloadKey((key) => key + 1)}>
              Попробовать снова
            </button>
          </section>
        )}

        {!loading && !error && report && (
          <>
            <section className="summary-section" aria-labelledby="summary-heading">
              <div className="section-heading">
                <div>
                  <p className="section-kicker">Сводка</p>
                  <h2 id="summary-heading">Общий итог</h2>
                </div>
                <p>на {formatDate(report.report_date)}</p>
              </div>
              <div className="summary-grid">
                <SummaryCard
                  label="Активные работы"
                  value={report.totals.active_works_amount}
                  hint="Без отменённых работ"
                />
                <SummaryCard
                  label="Уже оплачено"
                  value={report.totals.paid}
                  hint="Фактические выплаты"
                  tone="paid"
                />
                <SummaryCard
                  label="Осталось оплатить"
                  value={report.totals.remaining}
                  hint="По активным работам"
                  tone="remaining"
                />
                <SummaryCard
                  label="Не распределено"
                  value={report.totals.unallocated}
                  hint="Не отнесено на активные работы"
                />
              </div>
            </section>

            <section className="contracts-section" aria-labelledby="contracts-heading">
              <div className="section-heading contracts-heading">
                <div>
                  <p className="section-kicker">Детализация</p>
                  <h2 id="contracts-heading">Договоры и работы</h2>
                </div>
                <p>Договоров: {report.contracts.length}</p>
              </div>
              {report.contracts.length === 0 ? (
                <div className="empty-state">
                  <h3>Договоры не найдены</h3>
                  <p>Проверьте исходные файлы в папке data.</p>
                </div>
              ) : (
                <div className="contracts-list">
                  {report.contracts.map((contract) => (
                    <ContractCard key={contract.contract_id} contract={contract} />
                  ))}
                </div>
              )}
            </section>

            <aside className="method-note">
              <span className="method-icon" aria-hidden="true">i</span>
              <div>
                <h2>Как читать распределение</h2>
                <p>
                  Сначала учитываются платежи с указанной работой, затем общие авансы —
                  по порядку неотменённых работ. Запланированные работы участвуют в расчёте.
                </p>
              </div>
            </aside>
          </>
        )}

        <footer className="page-footer">
          <span>Суммы указаны в рублях, с точностью до копейки</span>
          <span>CSV → SQLite → отчёт</span>
        </footer>
      </main>
    </PageShell>
  );
}
