import React, { type ReactNode } from "react";
import { translate } from "@docusaurus/Translate";
import IconArrow from "@theme/Icon/Arrow";
import type { Props } from "@theme/DocSidebar/Desktop/CollapseButton";

export default function CollapseButton({ onClick }: Props): ReactNode {
  return (
    <button
      type="button"
      title={translate({
        id: "theme.docs.sidebar.collapseButtonTitle",
        message: "Collapse sidebar",
        description: "The title attribute for collapse button of doc sidebar",
      })}
      aria-label={translate({
        id: "theme.docs.sidebar.collapseButtonAriaLabel",
        message: "Collapse sidebar",
        description: "The title attribute for collapse button of doc sidebar",
      })}
      className="caracal-sidebar-toggle caracal-sidebar-toggle--collapse"
      onClick={onClick}
    >
      <IconArrow className="caracal-sidebar-toggle__icon caracal-sidebar-toggle__icon--collapse" />
    </button>
  );
}
