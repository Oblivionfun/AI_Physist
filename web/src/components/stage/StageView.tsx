import { BuilderColumn } from "./BuilderColumn";
import { CenterStage } from "./CenterStage";
import { ChannelBand } from "./ChannelBand";
import { LearnerColumn } from "./LearnerColumn";
import { Ribbon } from "./Ribbon";

export function StageView() {
  return (
    <div className="stage">
      <BuilderColumn />
      <CenterStage />
      <LearnerColumn />
      <ChannelBand />
      <Ribbon />
    </div>
  );
}
