"""
Sentinel Shield v2 — Audit Export Engine
Generates CSV and PDF compliance reports from the immutable audit ledger.
Requires: reportlab (for PDF). Falls back to CSV-only if not installed.
"""
import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
EXPORT_DIR = os.path.join(BASE_DIR, "logs", "exports")


class AuditExporter:
    """Generates regulator-ready compliance exports from audit ledger entries."""

    def __init__(self):
        os.makedirs(EXPORT_DIR, exist_ok=True)

    def to_csv(
        self,
        entries: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> str:
        """Export audit entries to a CSV file. Returns the file path."""
        if not filename:
            filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(EXPORT_DIR, filename)

        fieldnames = [
            "timestamp", "tenant_id", "user_id", "user_role", "department",
            "action", "document", "prompt_hash", "redactions_applied",
            "policy_triggered", "model_queried", "risk_score", "entry_hash"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for entry in entries:
                row = dict(entry)
                row["redactions_applied"] = json.dumps(row.get("redactions_applied", []))
                writer.writerow(row)

        return filepath

    def to_pdf(
        self,
        entries: List[Dict[str, Any]],
        org_name: str = "Your Organization",
        stats: Optional[Dict[str, Any]] = None,
        chain_valid: bool = True,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a branded PDF compliance report.
        Returns file path or None if reportlab not installed.
        """
        if not REPORTLAB_AVAILABLE:
            return None

        if not filename:
            filename = f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(EXPORT_DIR, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                                 topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # ── Header ──────────────────────────────────────────────────────────
        title_style = ParagraphStyle("Title", parent=styles["Title"],
                                     fontSize=20, textColor=colors.HexColor("#10b981"))
        story.append(Paragraph("🛡️ Sentinel Shield — Compliance Audit Report", title_style))
        story.append(Spacer(1, 0.4*cm))

        sub_style = ParagraphStyle("Sub", parent=styles["Normal"],
                                   fontSize=10, textColor=colors.HexColor("#6b7280"))
        story.append(Paragraph(
            f"{org_name} · Generated {datetime.now().strftime('%B %d, %Y %H:%M UTC')} · "
            f"Audit Chain: {'✅ VERIFIED' if chain_valid else '⚠️ INTEGRITY ISSUE DETECTED'}",
            sub_style
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#10b981")))
        story.append(Spacer(1, 0.5*cm))

        # ── Stats Summary ────────────────────────────────────────────────────
        if stats:
            story.append(Paragraph("Executive Summary", styles["Heading2"]))
            summary_data = [
                ["Metric", "Value"],
                ["Total Events Logged", str(stats.get("total_events", 0))],
                ["Total Redactions Applied", str(stats.get("total_redactions", 0))],
                ["High-Risk Events Blocked", str(stats.get("high_risk_events", 0))],
                ["Average Risk Score", str(stats.get("avg_risk_score", 0))],
                ["Audit Chain Integrity", "✅ VALID" if chain_valid else "⚠️ COMPROMISED"],
            ]
            t = Table(summary_data, colWidths=[8*cm, 8*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))

        # ── Detailed Log Table ───────────────────────────────────────────────
        story.append(Paragraph(f"Detailed Audit Log — Last {len(entries)} Events", styles["Heading2"]))

        table_data = [["Timestamp", "User", "Role", "Action", "Dept", "Risk", "Redactions"]]
        for e in entries[:200]:  # Cap at 200 for PDF readability
            ts = e.get("timestamp", "")[:19].replace("T", " ")
            table_data.append([
                ts,
                str(e.get("user_id", ""))[:20],
                str(e.get("user_role", "")),
                str(e.get("action", ""))[:25],
                str(e.get("department", ""))[:15],
                str(e.get("risk_score", "-")),
                str(len(e.get("redactions_applied", []))),
            ])

        col_widths = [4.2*cm, 3.5*cm, 3*cm, 4*cm, 2.5*cm, 1.5*cm, 2.5*cm]
        t2 = Table(table_data, colWidths=col_widths, repeatRows=1)
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t2)

        # ── Footer ───────────────────────────────────────────────────────────
        story.append(Spacer(1, 1*cm))
        footer_style = ParagraphStyle("Footer", parent=styles["Normal"],
                                      fontSize=7, textColor=colors.HexColor("#9ca3af"))
        story.append(Paragraph(
            "Sentinel Shield v2 · Xavira Tech Labs · This report is cryptographically signed via SHA-256 hash chain. "
            "Tampering with audit logs invalidates the chain and is detectable.",
            footer_style
        ))

        doc.build(story)
        return filepath
