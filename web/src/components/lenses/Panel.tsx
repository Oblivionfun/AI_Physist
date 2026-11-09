import type { ReactNode } from "react";

export function Panel({
  idx,
  title,
  note,
  className = "",
  children,
  tools,
}: {
  idx: string;
  title: string;
  note?: ReactNode;
  className?: string;
  children: ReactNode;
  tools?: ReactNode;
}) {
  return (
    <section className={`panel ${className}`}>
      <header className="panel-head">
        <p className="label">
          <b>{idx}</b> {title}
        </p>
        {tools}
      </header>
      {note && <p className="panel-note">{note}</p>}
      <div className="panel-body">{children}</div>
    </section>
  );
}
