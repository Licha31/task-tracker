import { useEffect, useState } from "react";

import { getTasks, updateTaskStatus } from "./api";
import { addDays, formatDateForApi, formatShortDate, startOfWeek } from "./dateUtils";
import type { Task, TaskStatus } from "./types";

type TaskFilter = "all" | "payroll" | "sales_tax";

type Props = {
  isAdmin: boolean;
};

function formatWeekLabel(start: Date, end: Date) {
  const startFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });
  const endFormatter = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return `${startFormatter.format(start)} – ${endFormatter.format(end)}`;
}

function statusLabel(status: TaskStatus) {
  return status === "in_progress"
    ? "In Progress"
    : status.charAt(0).toUpperCase() + status.slice(1);
}

function TrackerView({ isAdmin }: Props) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskFilter, setTaskFilter] = useState<TaskFilter>("all");
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const weekEnd = addDays(weekStart, 6);
  const filteredTasks = tasks.filter(
    (task) => taskFilter === "all" || task.task_type === taskFilter,
  );
  const payrollCount = tasks.filter((task) => task.task_type === "payroll").length;
  const salesTaxCount = tasks.filter((task) => task.task_type === "sales_tax").length;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    getTasks(formatDateForApi(weekStart), formatDateForApi(weekEnd))
      .then((data) => active && setTasks(data))
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Could not load tasks.");
      })
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [weekStart]);

  async function changeTaskStatus(taskId: number, status: TaskStatus) {
    try {
      setError("");
      await updateTaskStatus(taskId, status);
      setTasks((current) =>
        current.map((task) => (task.id === taskId ? { ...task, status } : task)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update status.");
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Weekly</h1>
          <p className="date-range">{formatWeekLabel(weekStart, weekEnd)}</p>
        </div>
        <div className="period-navigation">
          <button type="button" onClick={() => setWeekStart((date) => addDays(date, -7))}>
            ← Previous Week
          </button>
          <button type="button" onClick={() => setWeekStart((date) => addDays(date, 7))}>
            Next Week →
          </button>
        </div>
      </header>

      <nav className="task-filters" aria-label="Task filters">
        {(["all", "payroll", "sales_tax"] as const).map((filter) => {
          const count = filter === "all" ? tasks.length : filter === "payroll" ? payrollCount : salesTaxCount;
          const label = filter === "all" ? "All" : filter === "payroll" ? "Payroll" : "Sales Tax";
          return (
            <button
              type="button"
              className={taskFilter === filter ? "active" : ""}
              onClick={() => setTaskFilter(filter)}
              key={filter}
            >
              {label} <span>{count}</span>
            </button>
          );
        })}
      </nav>

      {error && <p className="form-error">{error}</p>}
      <section className="task-list" aria-busy={loading}>
        {!loading && filteredTasks.length > 0 && (
          <div className="task-list-header" aria-hidden="true">
            <span>Company</span>
            <span>Task type</span>
            <span>Process / Due</span>
            <span>Pay date</span>
            <span>Status</span>
          </div>
        )}
        {loading ? (
          <div className="empty-state">Loading operations…</div>
        ) : filteredTasks.length === 0 ? (
          <div className="empty-state">
            {tasks.length === 0 ? "No tasks scheduled for this week." : "No tasks found for this filter."}
          </div>
        ) : (
          filteredTasks.map((task) => (
            <article className="task-row" key={task.id}>
              <div className="task-company">
                <h2>{task.company_name}</h2>
              </div>

              <span className={`task-kind task-kind--${task.task_type}`}>
                {task.task_type === "payroll" ? "Payroll" : "Sales Tax"}
              </span>

              <div className="task-date">
                <span>{task.task_type === "payroll" ? "Process" : "Due date"}</span>
                <strong>{formatShortDate(task.process_date ?? task.due_date)}</strong>
              </div>

              <div className="task-date task-date--secondary">
                {task.task_type === "payroll" && (
                  <>
                    <span>Pay date</span>
                    <strong>{formatShortDate(task.pay_date)}</strong>
                  </>
                )}
              </div>

              <div className="task-actions">
                {isAdmin ? (
                  <select
                    className={`status-select status-select--${task.status}`}
                    aria-label={`Status for ${task.company_name}`}
                    value={task.status}
                    onChange={(event) => void changeTaskStatus(task.id, event.target.value as TaskStatus)}
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                ) : (
                  <span className={`status-label status-label--${task.status}`}>
                    {statusLabel(task.status)}
                  </span>
                )}
              </div>
            </article>
          ))
        )}
      </section>
    </section>
  );
}

export default TrackerView;
