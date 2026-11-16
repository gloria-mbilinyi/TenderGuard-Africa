import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ReportItem } from "../types";
import { ReportsPage } from "./ReportsPage";

const report: ReportItem = {
  filename: "EVL-0123456789ABCDEF_evaluation_report.md",
  bid_id: "EVL-0123456789ABCDEF",
  tender_title: "Supply of regional water pumps",
  supplier_names: ["Kijani Works Ltd", "Maji Supply Cooperative"],
  workspace_id: "EVL-0123456789ABCDEF",
  generated_at: "2026-11-16T10:30:00+03:00",
  approved_by: "Named Demo Authorizer",
  authorizer_identity_verified: false,
  status: "DRAFT_FOR_COMMITTEE_REVIEW",
  size_bytes: 12_288,
  modified_at: "2026-11-17T12:00:00Z",
  download_url: "/api/browser/reports/EVL-0123456789ABCDEF_evaluation_report.md/download",
};

describe("Report library", () => {
  it("uses dynamic tender and supplier metadata with a separate authorizer and protected download", () => {
    const { container } = render(<ReportsPage reports={[report]} />);
    expect(screen.getByRole("heading", { level: 4, name: report.tender_title! })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: report.filename })).toBeNull();
    expect(screen.getByText("Kijani Works Ltd vs Maji Supply Cooperative")).toBeTruthy();
    expect(screen.getByText(`Workspace: ${report.workspace_id}`)).toBeTruthy();
    expect(screen.getByText("Report generated")).toBeTruthy();
    expect(container.querySelector("time")?.getAttribute("datetime")).toBe(report.generated_at);
    expect(screen.getByText("Draft for committee review")).toBeTruthy();
    expect(screen.getByText("Report generation authorized by")).toBeTruthy();
    expect(screen.getByText("Named Demo Authorizer")).toBeTruthy();
    expect(screen.getByText("Recorded name; identity not independently verified")).toBeTruthy();
    const download = screen.getByRole("link", { name: `Download draft report: ${report.tender_title}` });
    expect(download.getAttribute("href")).toBe(report.download_url);
    expect(download.hasAttribute("download")).toBe(true);
  });

  it("keeps historical reports usable when the API has only the original fields", () => {
    const legacy: ReportItem = {
      filename: "BID-LEGACY_evaluation_report.md", bid_id: "BID-LEGACY",
      status: "DRAFT_FOR_COMMITTEE_REVIEW", size_bytes: 150,
      modified_at: "2026-10-01T08:00:00Z",
      download_url: "/api/browser/reports/BID-LEGACY_evaluation_report.md/download",
    };
    const { container } = render(<ReportsPage reports={[legacy]} />);
    expect(screen.getByRole("heading", { level: 4, name: legacy.filename })).toBeTruthy();
    expect(screen.getByText("Supplier details unavailable for this archived report")).toBeTruthy();
    expect(screen.getByText("Bid reference: BID-LEGACY")).toBeTruthy();
    expect(screen.getByText("File last updated")).toBeTruthy();
    expect(container.querySelector("time")?.getAttribute("datetime")).toBe(legacy.modified_at);
    expect(screen.getByText("Not recorded in this report")).toBeTruthy();
    expect(screen.getByRole("link", { name: `Download draft report: ${legacy.filename}` }).getAttribute("href")).toBe(legacy.download_url);
  });

  it("renders document-derived strings as plain text", () => {
    const unsafeText = '<img src=x onerror="alert(1)">';
    const { container } = render(<ReportsPage reports={[{
      ...report, tender_title: unsafeText, supplier_names: ["Single supplier"], approved_by: unsafeText,
    }]} />);
    expect(screen.getByRole("heading", { level: 4, name: unsafeText })).toBeTruthy();
    expect(screen.getByText("Single supplier")).toBeTruthy();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
  });

  it("handles empty libraries and invalid legacy dates", () => {
    const { rerender } = render(<ReportsPage reports={[]} />);
    expect(screen.getByText("No generated draft reports")).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();
    rerender(<ReportsPage reports={[{ ...report, generated_at: null, modified_at: "invalid-date" }]} />);
    expect(screen.getByText("Date unavailable")).toBeTruthy();
  });
});
