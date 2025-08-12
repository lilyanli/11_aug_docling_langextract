Extract the following fields from the text. If a field cannot be found, return null.

IMPORTANT: Only extract information that is explicitly stated in the text. Do not make up, infer, or hallucinate any information. If something is not clearly stated, return null.

Required JSON shape:
{
  "fund": {
    "fund_name": string|null,
    "fund_reporting_period": string|null, // ISO date string "YYYY-MM-DD" when available
    "vintage_year": number|null,
    "gp_name": string|null,
    "domicile": string|null,
    "strategy": string|null
  },
  "investments": [
    {
      "investment_name": string|null,
      "investment_type" : string|null,
      "industry": string|null,
      "country" : string|null,
      "currency" : string|null,
      "investment_date" : string|null,
      "investment_cost" : number|null,
      "fair_value" : number|null,
      "ownership" : number|null, // Percentage ownership, numeric value only, no "%" sign
      "number_of_shares" : number|null, 
      "moic" : number|null // multiple, numeric only
    }
  ],
  
  "fees": {
    "management_fee": string|null,
    "carry": string|null,
    "hurdle_rate": string|null,
    "catch_up": string|null
  },
  "contacts": [
    {"name": string|null, "title": string|null, "email": string|null, "phone": string|null}
  ],
  "source_anchors": string[]|null
}

Rules:
- Use exact values as stated in the document.
- Prefer structured amounts/percentages (e.g., "2% management fee").
- Dates must be ISO strings in the form "YYYY-MM-DD" when available.
- If multiple share classes exist, prefer the main fund's standard terms.
- Keep a list of any page anchors like "[PAGE=3]" you see near extracted text in "source_anchors".
- CRITICAL: Only extract investments from CURRENT investment sections like "Unaudited Valuation Report", "Schedule of Investments", or "Portfolio Holdings". DO NOT extract from "Future Pipeline", "Investment Pipeline", or similar sections showing planned investments.
- Extract ALL investments found in the current schedule of investments section.
- Each investment should be a separate object in the investments array.
- CRITICAL: Only extract information that is explicitly present in the text. Do not infer, assume, or create any information.
- If a field is not clearly stated in the text, return null for that field.
- Pay attention to the hierarchical structure: Investment Type > Country > Industry > Company
- The same company may appear multiple times with different investment types (e.g., Corporate Debt vs Equities)
- CRITICAL: Currency and Country are separate fields. Do not assume USD currency means United States country. Extract the actual country/geography separately from the currency.
