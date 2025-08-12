# exporters.py
from __future__ import annotations
from pathlib import Path
import uuid
import pandas as pd
from typing import Dict, Any, List
from schema import FundDocExtraction

def _uuid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def to_relational_rows(model: FundDocExtraction, fund_id: str) -> Dict[str, List[Dict[str, Any]]]:
    # ---- fund table (1 row)
    fund_row = {
        "fund_id": fund_id,
        "fund_name": model.fund.fund_name,
        "vintage_year": model.fund.vintage_year,
        "gp_name": model.fund.gp_name,
        "domicile": model.fund.domicile,
        "strategy": model.fund.strategy,
    }
    
    # ---- investment table (0..N rows)
    investment_rows = []
    for investment in model.investments:
        investment_row = {
            "investment_id": _uuid("inv"),
            "fund_id": fund_id,
            "investment_name": investment.investment_name,
            "investment_type": investment.investment_type,
            "industry": investment.industry,
            "country": investment.country,
            "currency": investment.currency,
            "investment_date": investment.investment_date,
            "investment_cost": investment.investment_cost,
            "fair_value": investment.fair_value,
            "ownership": investment.ownership,
            "number_of_shares": investment.number_of_shares,
            "moic": investment.moic,
        }
        investment_rows.append(investment_row)
    
    # ---- fees table (1 row)
    fee_row = {
        "fee_id": _uuid("fee"),
        "fund_id": fund_id,
        "management_fee": model.fees.management_fee,
        "carry": model.fees.carry,
        "hurdle_rate": model.fees.hurdle_rate,
        "catch_up": model.fees.catch_up,
    }

    # ---- contacts table (0..N)
    contact_rows = []
    for c in model.contacts:
        contact_rows.append({
            "contact_id": _uuid("ctc"),
            "fund_id": fund_id,
            "name": c.name,
            "title": c.title,
            "email": c.email,
            "phone": c.phone,
        })

    # ---- sources table (0..N)
    source_rows = []
    if model.source_anchors:
        for a in model.source_anchors:
            source_rows.append({
                "source_id": _uuid("src"),
                "fund_id": fund_id,
                "anchor": a,
            })

    return {
        "fund": [fund_row],
        "investments": investment_rows,  # Changed from single investment to list
        "fees": [fee_row],
        "contacts": contact_rows,
        "sources": source_rows,
    }

def write_csvs(tables: Dict[str, List[Dict[str, Any]]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        df = pd.DataFrame(rows)
        (out_dir / f"{name}.csv").write_text("", encoding="utf-8") if df.empty else None
        df.to_csv(out_dir / f"{name}.csv", index=False)

# ---- Optional: generate a simple PDF report for humans
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def write_pdf_report(model: FundDocExtraction, pdf_path: Path, fund_id: str):
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    x, y = 2*cm, height - 2*cm

    def line(txt: str):
        nonlocal y
        pdf.drawString(x, y, txt if txt is not None else "")
        y -= 0.7*cm
        if y < 2*cm:
            pdf.showPage()
            y = height - 2*cm

    pdf.setTitle(f"Fund Extraction Report - {fund_id}")
    pdf.setFont("Helvetica-Bold", 14)
    line(f"Fund Extraction Report")
    pdf.setFont("Helvetica", 10)
    line(f"Run ID (fund_id): {fund_id}")
    line("")

    pdf.setFont("Helvetica-Bold", 12)
    line("Fund")
    pdf.setFont("Helvetica", 10)
    line(f"Name: {model.fund.fund_name}")
    line(f"Vintage year: {model.fund.vintage_year}")
    line(f"GP: {model.fund.gp_name}")
    line(f"Domicile: {model.fund.domicile}")
    line(f"Strategy: {model.fund.strategy}")
    line("")

    pdf.setFont("Helvetica-Bold", 12)
    line("Fees")
    pdf.setFont("Helvetica", 10)
    line(f"Management fee: {model.fees.management_fee}")
    line(f"Carry: {model.fees.carry}")
    line(f"Hurdle rate: {model.fees.hurdle_rate}")
    line(f"Catch up: {model.fees.catch_up}")
    line("")

    if model.investments:
        pdf.setFont("Helvetica-Bold", 12)
        line("Investments")
        pdf.setFont("Helvetica", 10)
        for inv in model.investments:
            line(f"- {inv.investment_name} | {inv.investment_type} | {inv.industry} | {inv.country}")
            line(f"  Cost: {inv.investment_cost} | Fair Value: {inv.fair_value} | Ownership: {inv.ownership}%")
        line("")

    if model.contacts:
        pdf.setFont("Helvetica-Bold", 12)
        line("Contacts")
        pdf.setFont("Helvetica", 10)
        for c in model.contacts:
            line(f"- {c.name} | {c.title} | {c.email} | {c.phone}")
        line("")

    if model.source_anchors:
        pdf.setFont("Helvetica-Bold", 12)
        line("Source anchors")
        pdf.setFont("Helvetica", 10)
        for a in model.source_anchors:
            line(f"- {a}")

    pdf.save()
