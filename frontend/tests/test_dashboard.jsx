// --- AI-ASSISTED ---
// Tool: Claude Sonnet 4.6
// Prompt: "Create unit tests for a Next.js dashboard component with dual
//          upload zones, carrier table, score rings and detail panel."
// Modifications: Added fetch mocking strategy, file upload simulation,
//                score color/tier logic tests, filter behavior tests,
//                and detail panel interaction tests.
// --- END AI-ASSISTED ---

import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import Dashboard from "../app/dashboard";

// ─── Mock Data ────────────────────────────────────────────────────────────────
const mockCarriers = [
  {
    id: "1",
    carrier_id: "CA001",
    legal_name: "Alpha Transport LLC",
    dot_number: "1234567",
    authority_status: "Active",
    safety_rating: "Satisfactory",
    score: 82.5,
    fleet_size: 12,
    last_inspection_date: "2024-01-15",
    score_breakdown: {
      safety_rating_score: 20,
      oos_pct_score: 16,
      crash_total_score: 15,
      driver_oos_pct_score: 12,
      insurance_score: 10,
      authority_status_score: 9.5,
    },
  },
  {
    id: "2",
    carrier_id: "CA002",
    legal_name: "Beta Freight Inc",
    dot_number: "7654321",
    authority_status: "Inactive",
    safety_rating: "Conditional",
    score: 45.0,
    fleet_size: 5,
    last_inspection_date: "2023-11-20",
    score_breakdown: {
      safety_rating_score: 10,
      oos_pct_score: 8,
      crash_total_score: 10,
      driver_oos_pct_score: 8,
      insurance_score: 5,
      authority_status_score: 4,
    },
  },
  {
    id: "3",
    carrier_id: "CA003",
    legal_name: "Gamma Logistics",
    dot_number: "1122334",
    authority_status: "Revoked",
    safety_rating: "Unsatisfactory",
    score: 18.0,
    fleet_size: 2,
    last_inspection_date: null,
    score_breakdown: {
      safety_rating_score: 2,
      oos_pct_score: 4,
      crash_total_score: 3,
      driver_oos_pct_score: 4,
      insurance_score: 3,
      authority_status_score: 2,
    },
  },
];

const mockFetchCarriers = (overrides = {}) => ({
  results: mockCarriers,
  total: 3,
  at_risk_count: 1,
  ...overrides,
});

const mockHistory = {
  history: [
    { score: 80.0, computed_at: "2024-01-01T10:00:00Z" },
    { score: 75.0, computed_at: "2023-12-01T10:00:00Z" },
  ],
};

const mockUploadResult = {
  total_records: 3,
  new_count: 2,
  updated_count: 1,
  unchanged_count: 0,
  error_count: 0,
};

function setupFetchMock({
  carriersData,
  historyData,
  uploadData,
  failCarriers,
  failUpload,
} = {}) {
  return vi.spyOn(global, "fetch").mockImplementation((url) => {
    if (url.includes("/api/carriers/") && url.includes("/history/")) {
      if (historyData === "fail") {
        return Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(historyData || mockHistory),
      });
    }

    if (url.includes("/api/carriers/")) {
      if (failCarriers) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(carriersData || mockFetchCarriers()),
      });
    }

    if (url.includes("/api/ccf/upload/")) {
      if (failUpload) {
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ error: "Invalid file format" }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(uploadData || mockUploadResult),
      });
    }

    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe("Dashboard", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // ── Rendering ──────────────────────────────────────────────────────────────
  describe("initial render", () => {
    it("renders the dashboard title", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByText("FLEET SCORING")).toBeInTheDocument();
      expect(screen.getByText("DASHBOARD")).toBeInTheDocument();
    });

    it("renders the LIVE status indicator", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByText("LIVE")).toBeInTheDocument();
    });

    it("renders both upload zones", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByText("BASE CCF FILE")).toBeInTheDocument();
      expect(screen.getByText("MODIFIED CCF FILE")).toBeInTheDocument();
    });

    it("renders upload zone descriptions", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByText("INITIAL CARRIER DATA · ESTABLISHES BASELINE")).toBeInTheDocument();
      expect(screen.getByText("UPDATED CARRIER DATA · DETECTS CHANGES VIA HASH")).toBeInTheDocument();
    });

    it("renders table column headers", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByText("CARRIER")).toBeInTheDocument();
      expect(screen.getByText("DOT")).toBeInTheDocument();
      expect(screen.getByText("STATUS")).toBeInTheDocument();
      expect(screen.getByText("SAFETY")).toBeInTheDocument();
      expect(screen.getByText("SCORE")).toBeInTheDocument();
    });

    it("renders all 4 stat cards", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByText("TOTAL CARRIERS")).toBeInTheDocument();
      expect(screen.getByText("AVG SCORE")).toBeInTheDocument();
      expect(screen.getByText("AT RISK")).toBeInTheDocument();
      expect(screen.getByText("SAFE (>70)")).toBeInTheDocument();
    });

    it("renders filter buttons", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByText("ALL")).toBeInTheDocument();
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
      expect(screen.getByText("INACTIVE")).toBeInTheDocument();
      expect(screen.getByText("REVOKED")).toBeInTheDocument();
    });

    it("renders search input", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByPlaceholderText("SEARCH...")).toBeInTheDocument();
    });

    it("renders drop zone prompts", async () => {
      setupFetchMock();
      render(<Dashboard />);
      const prompts = screen.getAllByText("DROP .JSON OR CLICK TO SELECT");
      expect(prompts).toHaveLength(2);
    });

    it("renders footer text", async () => {
      setupFetchMock();
      render(<Dashboard />);
      expect(screen.getByText("CARRIER ASSURE · HASH-BASED CHANGE DETECTION ENGINE")).toBeInTheDocument();
    });
  });

});
