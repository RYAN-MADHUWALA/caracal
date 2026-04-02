import type { PropSidebar, PropSidebarItem, PropSidebarItemCategory } from "@docusaurus/plugin-content-docs";

function link(label: string, href: string): PropSidebarItem {
  return { type: "link", label, href };
}

function category(
  label: string,
  href: string,
  items: PropSidebarItem[],
  collapsible = true,
): PropSidebarItemCategory {
  return {
    type: "category",
    label,
    href,
    items,
    collapsible,
    collapsed: false,
  };
}

const openSourceSidebar = [
  category(
    "Open Source",
    "/open-source/overview",
    [
      category("End Users", "/open-source/end-users", [
        link("Installation", "/open-source/end-users/getting-started/installation"),
        link("Quickstart", "/open-source/end-users/getting-started/quickstart"),
        link("CLI", "/open-source/end-users/cli"),
        link("TUI", "/open-source/end-users/tui"),
        link("Configuration", "/open-source/end-users/configuration"),
        link("Commands", "/open-source/end-users/commands"),
        link("Workflows", "/open-source/end-users/workflows"),
        link("Troubleshooting", "/open-source/end-users/troubleshooting"),
        link("Security", "/open-source/end-users/security"),
        link("Concepts", "/open-source/end-users/concepts"),
      ]),
      category("Developers", "/open-source/developers", [
        link("Architecture", "/open-source/developers/architecture"),
        link("Contributing", "/open-source/developers/contributing"),
        link("Development Setup", "/open-source/developers/development-setup"),
        link("Testing", "/open-source/developers/testing"),
        link("Releases", "/open-source/developers/releases"),
        link("Changelog", "/open-source/developers/changelog"),
        link("Enterprise Connector", "/open-source/developers/enterprise-connector"),
      ]),
    ],
    false,
  ),
] satisfies PropSidebar;

const enterpriseSidebar = [
  category(
    "Enterprise",
    "/enterprise/overview",
    [
      link("Getting Started", "/enterprise/getting-started"),
      link("Configuration", "/enterprise/configuration"),
      link("Administration", "/enterprise/administration"),
      link("Access / Auth", "/enterprise/access-auth"),
      link("Deployment", "/enterprise/deployment"),
      link("Monitoring", "/enterprise/monitoring"),
      link("Troubleshooting", "/enterprise/troubleshooting"),
      link("Reference", "/enterprise/reference"),
    ],
    false,
  ),
] satisfies PropSidebar;

const buildSidebar = [
  category(
    "Build",
    "/build",
    [
      link("Architecture", "/open-source/developers/architecture"),
      link("Contributing", "/open-source/developers/contributing"),
      link("Development Setup", "/open-source/developers/development-setup"),
      link("Testing", "/open-source/developers/testing"),
      link("Releases", "/open-source/developers/releases"),
      link("Changelog", "/open-source/developers/changelog"),
    ],
    false,
  ),
] satisfies PropSidebar;

const manageSidebar = [
  category(
    "Manage",
    "/manage",
    [
      link("Installation", "/open-source/end-users/getting-started/installation"),
      link("Quickstart", "/open-source/end-users/getting-started/quickstart"),
      link("CLI", "/open-source/end-users/cli"),
      link("TUI", "/open-source/end-users/tui"),
      link("Configuration", "/open-source/end-users/configuration"),
      link("Workflows", "/open-source/end-users/workflows"),
      link("Administration", "/enterprise/administration"),
    ],
    false,
  ),
] satisfies PropSidebar;

const referenceSidebar = [
  category(
    "Reference",
    "/reference",
    [
      link("Commands", "/open-source/end-users/commands"),
      link("Concepts", "/open-source/end-users/concepts"),
      link("Architecture", "/open-source/developers/architecture"),
      link("Enterprise Reference", "/enterprise/reference"),
    ],
    false,
  ),
] satisfies PropSidebar;

const resourcesSidebar = [
  category(
    "Resources",
    "/resources",
    [
      link("Rulebook", "/resources/documentation-system/rulebook"),
      link("Security", "/open-source/end-users/security"),
      link("Troubleshooting", "/open-source/end-users/troubleshooting"),
      link("Contributor Calls", "/open-source/developers/contributing"),
    ],
    false,
  ),
] satisfies PropSidebar;

function pathMatches(pathname: string, href?: string): boolean {
  if (!href) {
    return false;
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

function containsActivePath(item: PropSidebarItem, pathname: string): boolean {
  if (item.type === "link") {
    return pathMatches(pathname, item.href);
  }

  if (item.type === "category") {
    if (pathMatches(pathname, item.href)) {
      return true;
    }

    return item.items.some((child) => containsActivePath(child, pathname));
  }

  return false;
}

function expandForActivePath(items: PropSidebar, pathname: string): PropSidebar {
  return items.map((item) => {
    if (item.type !== "category") {
      return item;
    }

    return {
      ...item,
      collapsed: item.collapsible ? !containsActivePath(item, pathname) : false,
      items: expandForActivePath(item.items, pathname),
    };
  });
}

export function getSidebarForPath(pathname: string): PropSidebar {
  if (pathname === "/") {
    return [];
  }

  if (pathname.startsWith("/open-source")) {
    return expandForActivePath(openSourceSidebar, pathname);
  }

  if (pathname.startsWith("/enterprise")) {
    return expandForActivePath(enterpriseSidebar, pathname);
  }

  if (pathname.startsWith("/build")) {
    return expandForActivePath(buildSidebar, pathname);
  }

  if (pathname.startsWith("/manage")) {
    return expandForActivePath(manageSidebar, pathname);
  }

  if (pathname.startsWith("/reference")) {
    return expandForActivePath(referenceSidebar, pathname);
  }

  if (pathname.startsWith("/resources")) {
    return expandForActivePath(resourcesSidebar, pathname);
  }

  return [];
}
