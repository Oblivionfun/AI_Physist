import type { Timed } from "../../data/fold";
import { elapsed } from "../../data/derive";

/** The agent's latest thought, de-emphasised: context for the visuals, not the content. */
export function Ticker({ item, now, label = "思考" }: { item?: Timed<string>; now: number; label?: string }) {
  if (!item) return null;
  const age = now - item.ts;
  const text = item.value.replace(/\*\*/g, "").replace(/\s+/g, " ").trim();
  return (
    <div className={`ticker ${age < 8 ? "fresh" : ""}`}>
      <span className="label">
        {label} <span className="mono">−{elapsed(age)}</span>
      </span>
      <p className="clamp-3">{text}</p>
    </div>
  );
}
