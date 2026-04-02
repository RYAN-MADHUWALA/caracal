export type SearchDocEntry = {
  title: string;
  url: string;
  breadcrumbs: string[];
  type: "doc";
};

export type NavigationAction = {
  title: string;
  description: string;
  to: string;
  keywords: string[];
  type: "navigation";
};

const navigationActions: NavigationAction[] = [
  {
    title: "Go to Open Source",
    description: "Browse the public runtime docs split into end users and developers.",
    to: "/open-source/overview",
    keywords: ["open source", "oss", "users", "developers"],
    type: "navigation",
  },
  {
    title: "Go to CLI",
    description: "Jump into the host and in-container command model.",
    to: "/open-source/end-users/cli",
    keywords: ["cli", "commands", "shell"],
    type: "navigation",
  },
  {
    title: "Go to Enterprise",
    description: "Open the enterprise user-facing documentation lane.",
    to: "/enterprise/overview",
    keywords: ["enterprise", "admin", "managed"],
    type: "navigation",
  },
  {
    title: "Go to Build",
    description: "Contributor setup, architecture, testing, and releases.",
    to: "/build",
    keywords: ["build", "development", "testing", "releases"],
    type: "navigation",
  },
  {
    title: "Go to Manage",
    description: "Operational hub for runtime management and configuration.",
    to: "/manage",
    keywords: ["manage", "operations", "workspaces", "configuration"],
    type: "navigation",
  },
  {
    title: "Go to Reference",
    description: "Reach command maps, concepts, and reference surfaces.",
    to: "/reference",
    keywords: ["reference", "api", "commands", "concepts"],
    type: "navigation",
  },
];

let searchDocsPromise: Promise<SearchDocEntry[]> | null = null;

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function includesAllTerms(haystack: string, query: string): boolean {
  const terms = normalize(query).split(/\s+/).filter(Boolean);
  return terms.every((term) => haystack.includes(term));
}

function scoreMatch(parts: string[], query: string): number {
  const normalizedQuery = normalize(query);
  if (!normalizedQuery) {
    return 0;
  }

  const title = normalize(parts[0] ?? "");
  const haystack = normalize(parts.join(" "));
  let score = 0;

  if (title === normalizedQuery) {
    score += 120;
  }
  if (title.startsWith(normalizedQuery)) {
    score += 72;
  }
  if (title.includes(normalizedQuery)) {
    score += 48;
  }
  if (haystack.includes(normalizedQuery)) {
    score += 20;
  }

  const terms = normalizedQuery.split(/\s+/).filter(Boolean);
  score += terms.filter((term) => title.includes(term)).length * 12;
  score += terms.filter((term) => haystack.includes(term)).length * 4;

  return score;
}

export async function loadSearchDocs(baseUrl: string): Promise<SearchDocEntry[]> {
  if (!searchDocsPromise) {
    searchDocsPromise = fetch(`${baseUrl}search-index.json`)
      .then((response) => response.json())
      .then((payload: Array<{ documents?: Array<Record<string, unknown>> }>) => {
        const map = new Map<string, SearchDocEntry>();

        payload.forEach((group) => {
          (group.documents ?? []).forEach((entry) => {
            if ("h" in entry) {
              return;
            }

            const title = typeof entry.t === "string" ? entry.t : null;
            const url = typeof entry.u === "string" ? entry.u : null;

            if (!title || !url) {
              return;
            }

            const breadcrumbs = Array.isArray(entry.b)
              ? entry.b.filter((item): item is string => typeof item === "string")
              : [];

            const key = `${url}::${title}`;
            if (!map.has(key)) {
              map.set(key, {
                title,
                url,
                breadcrumbs,
                type: "doc",
              });
            }
          });
        });

        return Array.from(map.values());
      });
  }

  return searchDocsPromise;
}

export function getNavigationResults(query: string, limit = 6): NavigationAction[] {
  if (!normalize(query)) {
    return navigationActions.slice(0, limit);
  }

  return navigationActions
    .map((item) => {
      const haystack = [item.title, item.description, ...item.keywords].join(" ").toLowerCase();
      return {
        item,
        score: scoreMatch([item.title, item.description, ...item.keywords], query),
        matches: includesAllTerms(haystack, query),
      };
    })
    .filter((entry) => entry.matches)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((entry) => entry.item);
}

export function getDocResults(docs: SearchDocEntry[], query: string, limit = 8): SearchDocEntry[] {
  if (!normalize(query)) {
    return docs.slice(0, limit);
  }

  return docs
    .map((doc) => {
      const parts = [doc.title, ...doc.breadcrumbs, doc.url];
      const haystack = parts.join(" ").toLowerCase();
      return {
        doc,
        score: scoreMatch(parts, query),
        matches: includesAllTerms(haystack, query),
      };
    })
    .filter((entry) => entry.matches)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((entry) => entry.doc);
}

export function getQuickActions(): NavigationAction[] {
  return navigationActions.slice(0, 5);
}

export function navigate(history: { push: (to: string) => void }, to: string): void {
  history.push(to);
}
