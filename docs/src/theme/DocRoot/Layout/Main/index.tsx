import React, { type ReactNode } from "react";
import clsx from "clsx";
import { useLocation } from "@docusaurus/router";
import type { Props } from "@theme/DocRoot/Layout/Main";
import styles from "./styles.module.css";

export default function DocRootLayoutMain({ hiddenSidebarContainer, children }: Props): ReactNode {
  const { pathname } = useLocation();
  const isLandingPage = pathname === "/";
  const enhanced = hiddenSidebarContainer || isLandingPage;

  return (
    <main className={clsx(styles.docMainContainer, enhanced && styles.docMainContainerEnhanced)}>
      <div
        className={clsx(
          "container padding-top--md padding-bottom--lg",
          enhanced && styles.docItemWrapperEnhanced,
        )}
      >
        {children}
      </div>
    </main>
  );
}
