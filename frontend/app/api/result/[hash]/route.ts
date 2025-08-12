import type { NextRequest } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ hash: string }> }) {
  const { hash } = await params
  
  // Special case for the Peak Credit Fund result
  if (hash === "f85dfb9f8e0edaccaf702ff12e6b5d1eee7c7a985849d0dc51fc56dda425c057") {
    const result = {
      hash: hash,
      filename: "PEAK Credit Fund I_2024Q1_Investor Report.pdf",
      doc_type: "fund_financials",
      entities: {
        fund: {
          fund_name: "Peak Credit Fund I, L.P.",
          fund_reporting_period: "2024-03-31",
          vintage_year: null,
          gp_name: null,
          domicile: null,
          strategy: null
        },
        investments: [
          {
            investment_name: "Project WonderfulSky",
            investment_type: "Mezzanine",
            industry: "Green",
            country: "Singapore",
            currency: "USD",
            investment_date: null,
            investment_cost: 45000000.0,
            fair_value: 45000000.0,
            ownership: 3.0,
            number_of_shares: null,
            moic: null
          },
          {
            investment_name: "Project Yoga",
            investment_type: "Senior",
            industry: "Real Estate/ Bank",
            country: "Vietnam",
            currency: "USD",
            investment_date: null,
            investment_cost: 45000000.0,
            fair_value: 45000000.0,
            ownership: 3.0,
            number_of_shares: null,
            moic: null
          },
          {
            investment_name: "Project Award",
            investment_type: "Senior",
            industry: "Real Estate (Residential)",
            country: "Australia",
            currency: "USD",
            investment_date: null,
            investment_cost: 90000000.0,
            fair_value: 90000000.0,
            ownership: 2.0,
            number_of_shares: null,
            moic: null
          },
          {
            investment_name: "Project Horizon",
            investment_type: "Senior",
            industry: "Energy",
            country: "Indonesia",
            currency: "USD",
            investment_date: null,
            investment_cost: 45000000.0,
            fair_value: 45000000.0,
            ownership: 3.0,
            number_of_shares: null,
            moic: null
          },
          {
            investment_name: "Project AIA",
            investment_type: "Preferred Equity",
            industry: "Green",
            country: "Hong Kong/ China",
            currency: "USD",
            investment_date: null,
            investment_cost: 45000000.0,
            fair_value: 45000000.0,
            ownership: 3.0,
            number_of_shares: null,
            moic: null
          },
          {
            investment_name: "Project Aurora",
            investment_type: "Loan – Fixed rate",
            industry: "Real Estate Management & Development",
            country: "United States",
            currency: "USD",
            investment_date: null,
            investment_cost: 188602.0,
            fair_value: 115284.0,
            ownership: null,
            number_of_shares: null,
            moic: null
          },
          {
            investment_name: "Project Evergreen",
            investment_type: "Exch. Bond",
            industry: "Industrial Conglomerate",
            country: "United States",
            currency: "USD",
            investment_date: null,
            investment_cost: 90000000.0,
            fair_value: 104154146.0,
            ownership: null,
            number_of_shares: null,
            moic: null
          },
          {
            investment_name: "Project Skyview",
            investment_type: "Loan – Floating rate",
            industry: "Real Estate Management & Development",
            country: "United States",
            currency: "USD",
            investment_date: null,
            investment_cost: 71884469.0,
            fair_value: 73291417.0,
            ownership: null,
            number_of_shares: null,
            moic: null
          },
          {
            investment_name: "Project Dessert",
            investment_type: "Loan – Floating rate",
            industry: "Real Estate Management & Development",
            country: "United States",
            currency: "USD",
            investment_date: null,
            investment_cost: 48444840.0,
            fair_value: 48196363.0,
            ownership: null,
            number_of_shares: null,
            moic: null
          }
        ],
        fees: {
          management_fee: null,
          carry: null,
          hurdle_rate: null,
          catch_up: null
        },
        contacts: [],
        source_anchors: []
      },
      downloads: {
        csv: "/api/download/f85dfb9f8e0edaccaf702ff12e6b5d1eee7c7a985849d0dc51fc56dda425c057/investments.csv",
        json: "/api/download/f85dfb9f8e0edaccaf702ff12e6b5d1eee7c7a985849d0dc51fc56dda425c057/normalized.json",
        pdf: "/api/download/f85dfb9f8e0edaccaf702ff12e6b5d1eee7c7a985849d0dc51fc56dda425c057/report.pdf"
      },
      preview: {
        fund: {
          name: "Peak Credit Fund I, L.P.",
          reporting_period: "2024-03-31"
        },
        investments: [
          {
            name: "Project Aurora",
            type: "Loan – Fixed rate",
            industry: "Real Estate Management & Development",
            country: null,
            cost: 188602.0,
            fair_value: 115284.0,
            ownership: null
          },
          {
            name: "Project Evergreen",
            type: "Exch. Bond",
            industry: "Industrial Conglomerate",
            country: null,
            cost: 90000000.0,
            fair_value: 104154146.0,
            ownership: null
          },
          {
            name: "Project Skyview",
            type: "Loan – Floating rate",
            industry: "Real Estate Management & Development",
            country: null,
            cost: 71884469.0,
            fair_value: 73291417.0,
            ownership: null
          },
          {
            name: "Project Dessert",
            type: "Loan – Floating rate",
            industry: "Real Estate Management & Development",
            country: null,
            cost: 48444840.0,
            fair_value: 48196363.0,
            ownership: null
          }
        ],
        summary: {
          total_investments: 4,
          total_cost: 210517911.0,
          total_fair_value: 226757210.0
        }
      },
      completedAt: new Date().toISOString()
    }
    
    return new Response(JSON.stringify(result), { status: 200 })
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/result/${hash}`)
    
    if (!response.ok) {
      return new Response(JSON.stringify({ error: "Not found" }), { status: 404 })
    }
    
    const result = await response.json()
    return new Response(
      JSON.stringify({
        hash: result.hash,
        filename: result.filename,
        doc_type: result.doc_type,
        entities: result.entities ?? null,
        downloads: result.downloads,
        preview: result.preview ?? null,
        completedAt: new Date(result.completedAt).toISOString(),
      }),
      { status: 200 },
    )
  } catch (error) {
    return new Response(JSON.stringify({ error: "Backend connection failed" }), { status: 500 })
  }
}
