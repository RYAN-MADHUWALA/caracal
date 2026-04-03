import React from "react";
import Link from "@docusaurus/Link";

type RelatedLink = {
  label: string;
  to: string;
};

type DocPlaceholderProps = {
  summary: string;
  audience: string;
  prerequisites?: string[];
  plannedSections?: string[];
  related?: RelatedLink[];
};

export default function DocPlaceholder({
  summary,
  audience,
  prerequisites = [],
  plannedSections = [],
  related = [],
}: DocPlaceholderProps): React.ReactElement {
  return (
    <div className="caracal-placeholder">
      <div className="caracal-placeholder__notice">
        This page defines the topic map and related entry points for this section.
      </div>

      <p className="caracal-placeholder__summary">{summary}</p>

      <div className="caracal-placeholder__grid">
        <section className="caracal-placeholder__panel">
          <h2>Audience</h2>
          <p>{audience}</p>
        </section>

        <section className="caracal-placeholder__panel">
          <h2>Prerequisites</h2>
          {prerequisites.length > 0 ? (
            <ul className="caracal-placeholder__list">
              {prerequisites.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p>No prerequisites are listed for this topic.</p>
          )}
        </section>

        <section className="caracal-placeholder__panel">
          <h2>Quick Start / Overview</h2>
          <p>This section is where the main entry path for the topic is organized.</p>
        </section>

        <section className="caracal-placeholder__panel">
          <h2>Core Explanation</h2>
          {plannedSections.length > 0 ? (
            <ul className="caracal-placeholder__list">
              {plannedSections.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p>This section collects the core concepts and behaviors for the topic.</p>
          )}
        </section>

        <section className="caracal-placeholder__panel">
          <h2>Examples</h2>
          <p>Examples, sample flows, and concrete usage patterns belong in this section.</p>
        </section>

        <section className="caracal-placeholder__panel">
          <h2>Edge Cases</h2>
          <p>Failure modes, limits, and operational edge cases belong in this section.</p>
        </section>

        <section className="caracal-placeholder__panel">
          <h2>Troubleshooting</h2>
          <p>Diagnostic checks, expected outputs, and escalation guidance belong in this section.</p>
        </section>

        <section className="caracal-placeholder__panel">
          <h2>Related Pages</h2>
          {related.length > 0 ? (
            <ul className="caracal-placeholder__list">
              {related.map((item) => (
                <li key={item.to}>
                  <Link to={item.to}>{item.label}</Link>
                </li>
              ))}
            </ul>
          ) : (
            <p>Related pages appear here when adjacent topics are available.</p>
          )}
        </section>
      </div>
    </div>
  );
}
