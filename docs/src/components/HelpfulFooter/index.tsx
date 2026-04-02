import React, { useState } from "react";

export default function HelpfulFooter(): React.ReactElement {
  const [choice, setChoice] = useState<"yes" | "no" | null>(null);

  return (
    <div className="caracal-helpful">
      <div className="caracal-helpful__heading">Is this helpful?</div>
      <div className="caracal-helpful__buttons">
        <button
          className="caracal-helpful__button"
          data-selected={choice === "yes"}
          onClick={() => setChoice("yes")}
          type="button"
        >
          Yes
        </button>
        <button
          className="caracal-helpful__button caracal-helpful__button--ghost"
          data-selected={choice === "no"}
          onClick={() => setChoice("no")}
          type="button"
        >
          No
        </button>
      </div>
      {choice ? <div className="caracal-helpful__text">Recorded: {choice}</div> : null}
    </div>
  );
}
