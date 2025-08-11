Extract the following fields from the text. If a field cannot be found, return null.

Required JSON shape:
{
  "fund": {
    "fund_name": string|null,
    "vintage_year": number|null,
    "gp_name": string|null,
    "domicile": string|null,
    "strategy": string|null
  },
  "investment": {
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
  },
  
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
- If multiple share classes exist, prefer the main fund’s standard terms.
- Keep a list of any page anchors like "[PAGE=3]" you see near extracted text in "source_anchors".
