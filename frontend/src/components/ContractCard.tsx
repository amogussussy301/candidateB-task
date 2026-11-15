import type { ContractReport, WorkStatus } from "../api";
import { formatMoney } from "../format";

const STATUS_LABELS: Record<WorkStatus, string> = {
  planned: "Запланирована",
  done: "Выполнена",
  cancelled: "Отменена",
};

interface ContractCardProps {
  contract: ContractReport;
}

export function ContractCard({ contract }: ContractCardProps) {
  const hasUnallocated = contract.unallocated !== "0.00";

  return (
    <article className="contract-card" aria-labelledby={`contract-${contract.contract_id}`}>
      <header className="contract-header">
        <div className="contract-identity">
          <div className="contract-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M7 3.5h7l4 4V20.5H7a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z" />
              <path d="M14 3.5v4h4M9 12h6M9 16h5" />
            </svg>
          </div>
          <div>
            <p className="contract-number">Договор {contract.contract_id}</p>
            <h2 id={`contract-${contract.contract_id}`}>{contract.contractor}</h2>
          </div>
        </div>
        <div className="contract-percent" aria-label={`Оплачено ${contract.paid_percent}%`}>
          <strong>{contract.paid_percent}%</strong>
          <span>оплачено</span>
        </div>
      </header>

      <div className="contract-progress">
        <div className="progress-caption">
          <span>Оплата активных работ</span>
          <span>{formatMoney(contract.remaining)} осталось</span>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-label={`Оплата по договору ${contract.contract_id}`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={contract.paid_percent}
        >
          <span style={{ width: `${contract.paid_percent}%` }} />
        </div>
      </div>

      <dl className="contract-metrics">
        <div>
          <dt>Сумма договора</dt>
          <dd>{formatMoney(contract.contract_amount)}</dd>
        </div>
        <div>
          <dt>Активные работы</dt>
          <dd>{formatMoney(contract.active_works_amount)}</dd>
        </div>
        <div className="metric-paid">
          <dt>Уже оплачено</dt>
          <dd>{formatMoney(contract.paid)}</dd>
        </div>
        <div className="metric-remaining">
          <dt>Осталось оплатить</dt>
          <dd>{formatMoney(contract.remaining)}</dd>
        </div>
      </dl>

      {hasUnallocated && (
        <div className="unallocated-note" role="note">
          <span>Не распределено по работам</span>
          <strong>{formatMoney(contract.unallocated)}</strong>
        </div>
      )}

      <div className="works-table-wrap">
        <table className="works-table">
          <caption>Работы по договору {contract.contract_id}</caption>
          <thead>
            <tr>
              <th scope="col">Работа</th>
              <th scope="col">Статус</th>
              <th scope="col" className="numeric">Цена</th>
              <th scope="col" className="numeric">Оплачено</th>
              <th scope="col" className="numeric">Остаток</th>
            </tr>
          </thead>
          <tbody>
            {contract.works.map((work) => (
              <tr key={work.work_id} className={work.status === "cancelled" ? "is-cancelled" : ""}>
                <td className="work-name" data-label="Работа">
                  <span>{work.title}</span>
                  <small>{work.work_id}</small>
                  {work.status === "cancelled" && (
                    <small className="exclusion-note">Не входит в активный итог</small>
                  )}
                </td>
                <td data-label="Статус">
                  <span className={`status-badge status-${work.status}`}>
                    <span aria-hidden="true" />
                    {STATUS_LABELS[work.status]}
                  </span>
                </td>
                <td className="numeric money-cell" data-label="Цена">
                  {formatMoney(work.price)}
                </td>
                <td className="numeric money-cell paid-cell" data-label="Оплачено">
                  {formatMoney(work.paid)}
                </td>
                <td className="numeric money-cell remaining-cell" data-label="Остаток">
                  {formatMoney(work.remaining)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
