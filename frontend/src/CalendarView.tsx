import { useEffect, useMemo, useState } from "react";

import { getTasks } from "./api";
import { addDays, formatDateForApi, formatShortDate, startOfWeek } from "./dateUtils";
import type { Task, TaskStatus } from "./types";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function statusLabel(status: TaskStatus) {
  return status === "in_progress"
    ? "In Progress"
    : status.charAt(0).toUpperCase() + status.slice(1);
}

function taskDate(task: Task) {
  return task.task_type === "payroll" ? task.process_date : task.due_date;
}

function CalendarView() {
  const [month, setMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const [selectedDate, setSelectedDate] = useState(() => formatDateForApi(new Date()));
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const gridStart = useMemo(() => startOfWeek(month), [month]);
  const days = useMemo(() => Array.from({ length: 42 }, (_, index) => addDays(gridStart, index)), [gridStart]);
  const gridEnd = days[days.length - 1];
  const tasksByDate = useMemo(() => {
    const grouped = new Map<string, Task[]>();
    for (const task of tasks) {
      const date = taskDate(task);
      if (date) grouped.set(date, [...(grouped.get(date) ?? []), task]);
    }
    return grouped;
  }, [tasks]);
  const selectedTasks = tasksByDate.get(selectedDate) ?? [];

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getTasks(formatDateForApi(gridStart), formatDateForApi(gridEnd))
      .then((data) => active && setTasks(data))
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Could not load calendar.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [gridStart, gridEnd]);

  function changeMonth(offset: number) {
    const next = new Date(month.getFullYear(), month.getMonth() + offset, 1);
    setMonth(next);
    setSelectedDate(formatDateForApi(next));
  }

  return (
    <section>
      <header className="page-header calendar-header">
        <div>
          <h1>Calendar</h1>
          <p className="date-range">
            {new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" }).format(month)}
          </p>
        </div>
        <div className="period-navigation">
          <button type="button" onClick={() => changeMonth(-1)}>← Previous Month</button>
          <button type="button" onClick={() => changeMonth(1)}>Next Month →</button>
        </div>
      </header>

      {error && <p className="form-error">{error}</p>}
      <div className="calendar-layout" aria-busy={loading}>
        <div className="calendar-scroll">
          <div className="calendar-grid">
            {WEEKDAYS.map((day) => <div className="weekday" key={day}>{day}</div>)}
            {days.map((day) => {
              const key = formatDateForApi(day);
              const dayTasks = tasksByDate.get(key) ?? [];
              const outsideMonth = day.getMonth() !== month.getMonth();
              return (
                <button
                  type="button"
                  className={`calendar-day${outsideMonth ? " outside-month" : ""}${selectedDate === key ? " selected" : ""}`}
                  aria-label={`${key}, ${dayTasks.length} tasks`}
                  aria-pressed={selectedDate === key}
                  onClick={() => setSelectedDate(key)}
                  key={key}
                >
                  <span className="day-number">{day.getDate()}</span>
                  <span className="day-tasks">
                    {dayTasks.slice(0, 3).map((task) => (
                      <span className={`calendar-task calendar-task--${task.task_type}`} key={task.id}>
                        <strong>{task.company_name}</strong>
                        <small>
                          {task.task_type === "payroll"
                            ? `Payroll · ${task.source_label} · ${task.source_jurisdiction}`
                            : `Sales Tax · ${task.source_jurisdiction}`}
                        </small>
                      </span>
                    ))}
                    {dayTasks.length > 3 && <small className="more-tasks">+{dayTasks.length - 3} more</small>}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <aside className="day-detail" aria-live="polite">
          <header>
            <span>Selected date</span>
            <h2>{new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" }).format(new Date(`${selectedDate}T00:00:00`))}</h2>
          </header>
          {loading ? (
            <p className="detail-empty">Loading operations…</p>
          ) : selectedTasks.length === 0 ? (
            <p className="detail-empty">No operations scheduled.</p>
          ) : (
            <div className="detail-list">
              {selectedTasks.map((task) => (
                <article className="detail-task" key={task.id}>
                  <div>
                    <span className={`task-kind task-kind--${task.task_type}`}>
                      {task.task_type === "payroll" ? "Payroll" : "Sales Tax"}
                    </span>
                    <h3>{task.company_name}</h3>
                    <p className="detail-source">
                      {task.task_type === "payroll"
                        ? `${task.source_label} · ${task.source_jurisdiction}`
                        : task.source_jurisdiction}
                    </p>
                  </div>
                  <dl>
                    {task.task_type === "payroll" ? (
                      <>
                        <div><dt>Process date</dt><dd>{formatShortDate(task.process_date)}</dd></div>
                        <div><dt>Pay date</dt><dd>{formatShortDate(task.pay_date)}</dd></div>
                      </>
                    ) : (
                      <div><dt>Due date</dt><dd>{formatShortDate(task.due_date)}</dd></div>
                    )}
                    <div><dt>Status</dt><dd><span className={`status-label status-label--${task.status}`}>{statusLabel(task.status)}</span></dd></div>
                  </dl>
                </article>
              ))}
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

export default CalendarView;
