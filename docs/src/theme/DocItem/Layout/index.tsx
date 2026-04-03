import React, { type ReactNode } from "react";
import type { Props } from "@theme/DocItem/Layout";
import DocItemLayoutOriginal from "@theme-original/DocItem/Layout";

export default function DocItemLayout(props: Props): ReactNode {
  return (
    <div className="caracal-docitem-layout-single-rail">
      <DocItemLayoutOriginal {...props} />
    </div>
  );
}
