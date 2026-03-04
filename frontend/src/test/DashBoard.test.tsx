import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Dashboard from "../Dashboard";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const mockCarriersResponse = {
  results: [
    {
      id: 1,
      carrier_id: "C001",
      legal_name: "Alpha Logistics",
      dot_number: "123456",
      authority_status: "Active",
      safety_rating: "Satisfactory",
      score: 82,
      score_breakdown: {},
    },
    {
      id: 2,
      carrier_id: "C002",
      legal_name: "Beta Transport",
      dot_number: "654321",
      authority_status: "Inactive",
      safety_rating: "Conditional",
      score: 45,
      score_breakdown: {},
    },
  ],
  total: 2,
  at_risk_count: 1,
};

describe("Dashboard - Full Coverage", () => {
  beforeEach(() => {
    global.fetch = vi.fn((url: RequestInfo | URL) => {
      const urlStr = typeof url === "string" ? url : url.toString();

      if (urlStr.includes("/api/carriers/")) {
        return Promise.resolve(
          new Response(JSON.stringify(mockCarriersResponse), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }

      if (urlStr.includes("/api/ccf/upload/")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              new_count: 1,
              updated_count: 1,
              unchanged_count: 0,
              error_count: 0,
            }),
            { status: 200 }
          )
        );
      }

      if (urlStr.includes("/history/")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              history: [
                { score: 70, computed_at: new Date().toISOString() },
              ],
            }),
            { status: 200 }
          )
        );
      }

      return Promise.reject("Unknown endpoint");
    }) as unknown as typeof global.fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("renders loading state", async () => {
    render(<Dashboard />);
    expect(screen.getByText(/LOADING/i)).toBeInTheDocument();
  });

  test("loads carriers and stats", async () => {
    render(<Dashboard />);

    await waitFor(() =>
      expect(screen.getByText("Alpha Logistics")).toBeInTheDocument()
    );

    expect(
      screen.getByText(/TOTAL/i).parentElement
    ).toHaveTextContent("2");

    expect(
      screen.getByText(/AT RISK/i).parentElement
    ).toHaveTextContent("1");
  });

  test("filters by search", async () => {
    render(<Dashboard />);

    await waitFor(() =>
      expect(screen.getByText("Alpha Logistics")).toBeInTheDocument()
    );

    fireEvent.change(screen.getByPlaceholderText("SEARCH..."), {
      target: { value: "beta" },
    });

    expect(screen.queryByText("Alpha Logistics")).not.toBeInTheDocument();
    expect(screen.getByText("Beta Transport")).toBeInTheDocument();
  });

  test("opens and closes detail modal", async () => {
    render(<Dashboard />);

    await waitFor(() =>
      expect(screen.getByText("Alpha Logistics")).toBeInTheDocument()
    );

    fireEvent.click(screen.getByText("Alpha Logistics"));

    await waitFor(() =>
      expect(screen.getByText(/SCORE BREAKDOWN/i)).toBeInTheDocument()
    );

    fireEvent.click(screen.getByText("CLOSE"));

    await waitFor(() =>
      expect(screen.queryByText(/SCORE BREAKDOWN/i)).not.toBeInTheDocument()
    );
  });

  test("handles BASE upload and shows toast", async () => {
    render(<Dashboard />);

    const file = new File(["{}"], "base.json", {
      type: "application/json",
    });

    const inputs = document.querySelectorAll("input[type='file']");
    fireEvent.change(inputs[0], { target: { files: [file] } });

    await waitFor(() =>
      expect(screen.getByText(/BASE FILE/i)).toBeInTheDocument()
    );
  });

  test("handles MODIFIED upload", async () => {
    render(<Dashboard />);

    const file = new File(["{}"], "modified.json", {
      type: "application/json",
    });

    const inputs = document.querySelectorAll("input[type='file']");
    fireEvent.change(inputs[1], { target: { files: [file] } });

    await waitFor(() =>
      expect(screen.getByText(/MODIFIED FILE/i)).toBeInTheDocument()
    );
  });

  test("handles upload error", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ error: "Upload failed" }), {
          status: 400,
        })
      )
    ) as unknown as typeof global.fetch;

    render(<Dashboard />);

    const file = new File(["{}"], "error.json", {
      type: "application/json",
    });

    const input = document.querySelector("input[type='file']");
    fireEvent.change(input!, { target: { files: [file] } });

    await waitFor(() =>
      expect(screen.getByText(/Upload failed/i)).toBeInTheDocument()
    );
  });

  test("shows empty state when no carriers", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({ results: [], total: 0, at_risk_count: 0 }),
          { status: 200 }
        )
      )
    ) as unknown as typeof global.fetch;

    render(<Dashboard />);

    await waitFor(() =>
      expect(
        screen.getByText(/NO CARRIERS/i)
      ).toBeInTheDocument()
    );
  });
});