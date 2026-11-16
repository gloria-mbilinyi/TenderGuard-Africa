import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import type { CatalogTender } from "../types";
import { EvaluationPage } from "./EvaluationPage";

it("shows bid evidence and availability without submission timestamps or portal claims", async () => {
  const onEvaluate = vi.fn().mockResolvedValue(undefined);
  const tender: CatalogTender = {
    tender_id: "TG-DEMO-001",
    ocid: null,
    title: "Synthetic ICT procurement",
    description: "Synthetic supplier selection test",
    status: "active",
    procurement_method: "open",
    submission_deadline: "2026-10-10T12:00:00+03:00",
    amount: 45_000_000,
    currency: "TZS",
    procuring_entity: "Synthetic buyer",
    required_documents: [],
    eligibility_requirements: [],
    source_file: "data/ocds/demo_tender.json",
    synthetic: true,
    bids: [{
      bid_id: "BID-BETA-001",
      supplier_name: "Beta Systems Ltd",
      supplier_identifier: "SYNTH-BETA-001",
      amount: 47_000_000,
      currency: "TZS",
      submitted_at: "2026-10-09T11:30:00+03:00",
      submitted_document_codes: ["BID_FORM", "BUSINESS_LICENSE"],
      synthetic: true,
    }],
  };
  render(<EvaluationPage tenders={[tender]} result={null} onEvaluate={onEvaluate} />);

  expect(screen.getByText("Beta Systems Ltd")).toBeTruthy();
  expect(screen.getByText("BID-BETA-001")).toBeTruthy();
  expect(screen.getByText(/47,000,000/)).toBeTruthy();
  expect(screen.getByText("2 documents supplied")).toBeTruthy();
  expect(screen.getByText("Available for evaluation")).toBeTruthy();
  expect(screen.getByText("Submission deadline")).toBeTruthy();
  expect(screen.queryByText(/11:30|Submitted |accepted/i)).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "Evaluate tender" }));
  expect(onEvaluate).toHaveBeenCalledWith("TG-DEMO-001", "BID-BETA-001");
});
