import json
import os
import sqlite3
import httpx


def records(db, sql, params=()):
    return [dict(r) for r in db.execute(sql, params).fetchall()]


def retrieve(db: sqlite3.Connection, question: str):
    q = question.casefold()
    if "otif" in q:
        intent = "otif"
        rows = records(db, "SELECT carrier_id, SUM(shipments) shipments, 1.0*SUM(otif_count)/SUM(shipments) otif, 1.0*SUM(late_count)/SUM(shipments) late_rate FROM agg_logistics GROUP BY carrier_id ORDER BY otif LIMIT 5")
        failures = records(db, "SELECT SUM(CASE WHEN on_time=0 THEN 1 ELSE 0 END) late_shipments, SUM(CASE WHEN in_full=0 THEN 1 ELSE 0 END) short_shipments, SUM(CASE WHEN on_time=0 AND in_full=0 THEN 1 ELSE 0 END) both_failures, COUNT(*) shipments FROM fact_shipment")[0]
        return intent, {"carriers": rows, "failure_counts": failures}
    if "supplier" in q:
        return "suppliers", records(db, "SELECT supplier_id,supplier_name,supplier_otif,fill_rate,average_lead_time,late_delivery_rate FROM agg_supplier WHERE deliveries>0 ORDER BY supplier_otif LIMIT 5")
    if "backlog" in q or "facility" in q:
        return "backlog", records(db, "SELECT facility_id,facility_name,backlog_quantity,fulfillment_rate FROM agg_facility ORDER BY backlog_quantity DESC LIMIT 5")
    if "forecast" in q or "next month" in q or "expected" in q:
        return "forecast", records(db, "SELECT forecast_date,SUM(prediction) prediction FROM forecast_demand GROUP BY forecast_date ORDER BY forecast_date")
    if "excess" in q or "surplus" in q:
        return "excess", records(db, "SELECT product_id,facility_id,forecast_date,projected_ending_inventory,days_of_inventory FROM projected_inventory WHERE horizon=1 AND excess_inventory_flag=1 ORDER BY projected_ending_inventory DESC LIMIT 5")
    if "stockout" in q or "risk" in q:
        return "stockout", records(db, "SELECT product_id,facility_id,forecast_date,projected_ending_inventory,stockout_date,replenishment_quantity FROM projected_inventory WHERE stockout_flag=1 ORDER BY horizon,projected_ending_inventory LIMIT 5")
    if "exception" in q or "critical" in q:
        return "exceptions", records(db, "SELECT exception_id,type,severity,facility_id,product_id,actual_value,status,recommended_action FROM supply_chain_exception WHERE status IN ('Open','Investigating') ORDER BY CASE severity WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,exception_id LIMIT 5")
    return "unsupported", []


def fallback(intent, evidence):
    if intent == "unsupported":
        return "Ask about stockout risk, excess inventory, suppliers, OTIF, facility backlog, next-month demand, or critical exceptions."
    if not evidence:
        return f"No matching {intent} records in this synthetic snapshot."
    if intent == "otif":
        f = evidence["failure_counts"]
        return f"Among {f['shipments']} synthetic shipments, {f['late_shipments']} were late and {f['short_shipments']} were short; {f['both_failures']} failed both. These are observed failure categories; causes need operational investigation."
    if intent == "suppliers":
        r = evidence[0]
        return f"Lowest supplier OTIF: {r['supplier_name']} ({r['supplier_otif']:.1%}); fill rate {r['fill_rate']:.1%}, average lead time {r['average_lead_time']:.1f} days. Review delivery recovery and alternate allocations."
    if intent == "backlog":
        r = evidence[0]
        return f"{r['facility_name']} has the largest backlog: {r['backlog_quantity']:,.0f} units; order fulfillment {r['fulfillment_rate']:.1%}. Prioritize overdue orders and review material availability."
    if intent == "forecast":
        r = evidence[0]
        return f"Expected synthetic demand for {r['forecast_date']}: {r['prediction']:,.0f} units. This is a point forecast selected through chronological validation."
    if intent in ("stockout", "excess"):
        r = evidence[0]
        return f"Product {r['product_id']} at facility {r['facility_id']} has projected ending inventory {r['projected_ending_inventory']:,.1f} units for {r['forecast_date']}. "+("Expedite supply or schedule production." if intent == "stockout" else "Reduce replenishment or rebalance surplus.")
    r = evidence[0]
    return f"Priority exception {r['exception_id']}: {r['type']} ({r['severity']}, {r['status']}). {r['recommended_action']}"


def answer(db, question: str, use_llm=False):
    intent, evidence = retrieve(db, question)
    result = {"mode": "deterministic", "intent": intent, "answer": fallback(intent, evidence), "evidence": evidence, "synthetic_only": True, "limitation": "Snapshot analytics and assumptions; no causal proof or autonomous actions."}
    key = os.getenv("LLM_API_KEY")
    if use_llm and key and intent != "unsupported":
        try:
            response = httpx.post(os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")+"/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": os.getenv("LLM_MODEL", "gpt-4.1-mini"), "temperature": 0, "messages": [{"role": "system", "content": "Explain only the supplied fictional PackRight synthetic evidence. Distinguish assumptions and observed failures from causal proof. Never claim confidential company data or perform actions."}, {"role": "user", "content": json.dumps({"question": question, "evidence": evidence})}]}, timeout=15)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty model response")
            result.update(mode="llm", answer=content)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            result["fallback_reason"] = "Provider unavailable or invalid response; deterministic retrieval used."
    return result

