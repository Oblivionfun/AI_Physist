/** Theory of instance X evaluated on instance Y: knowledge from interaction stays on the diagonal. */
export function SwapMatrix({ swap, round }: { swap?: Record<string, number | string | null>; round: number }) {
  const cell = (k: string) => {
    const v = swap?.[k];
    return typeof v === "number" ? v : null;
  };
  const rows: [string, string][] = [
    ["A_on_A", "A_on_B"],
    ["B_on_A", "B_on_B"],
  ];
  return (
    <figure className="swap">
      <figcaption className="label">R{round}</figcaption>
      <table>
        <thead>
          <tr>
            <th />
            <th>用在 A</th>
            <th>用在 B</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <th>{i ? "B 的理论" : "A 的理论"}</th>
              {r.map((k) => {
                const v = cell(k);
                const diag = k === "A_on_A" || k === "B_on_B";
                return (
                  <td key={k} className={diag ? "diag" : "off"} style={{ background: v == null ? undefined : `rgba(20,24,27,${0.08 + 0.72 * v})`, color: v != null && v > 0.5 ? "#fbfcfc" : undefined }}>
                    {v == null ? "—" : `${Math.round(v * 100)}%`}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {typeof swap?.note === "string" && <p className="muted small">{swap.note}</p>}
    </figure>
  );
}
