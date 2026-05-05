# Available test IDs are passed in at runtime so the prompt always reflects the
# client's current LAB_TESTS catalog (lab definitions live in the app).
LAB_SCAN_PROMPT_TEMPLATE = """You are an expert Indian lab report parser. Extract every test value visible.

Return ONLY valid JSON (no markdown):
{{
  "reportDate": "YYYY-MM-DD if visible (else null)",
  "results": [
    {{ "testId": "id from list below", "value": "number or qualitative result (e.g. '12.5', 'Positive', '1:160', 'Nil')" }}
  ]
}}

AVAILABLE TEST IDS (id:name:unit):
{tests}

NAME MAPPING (common Indian lab synonyms):
- Hemoglobin/Hgb → hb
- TLC/WBC/Total Leukocyte → wbc
- Platelet/PLT → platelets
- ESR/Sedimentation → esr
- CRP → crp
- SGPT/ALT → sgpt
- SGOT/AST → sgot
- S.Creatinine/Creatinine → creatinine
- Blood Urea → urea
- RBS/Random Blood Sugar → rbs
- Vitamin D / 25-OH Vit D → vitd
- Vitamin B12 → vitb12
- Uric Acid → uricacid
- Complement C3 → c3
- Complement C4 → c4
- Total Cholesterol/Cholesterol → tchol
- LDL → ldl
- HDL → hdl
- Triglycerides/TG → trig
- ANA → ana
- Rheumatoid Factor/RF → rf
- Anti-CCP/CCP → anticcp
- Anti-dsDNA/dsDNA → antidsdna
- ANCA → anca
- HLA-B27 → hlab27

RULES:
- Only include tests actually visible in the report.
- For numeric tests, "value" must be a number as a string (no units).
- For qualitative tests (Urine R/M, ANA, ANCA, HLA-B27), use the verbatim result word/titre.
- Skip rows that are not in the test ID list.

Return ONLY JSON, no explanation."""


def build_lab_scan_prompt(tests: list[tuple[str, str, str]]) -> str:
    """tests is a list of (id, name, unit) tuples."""
    block = "\n".join(f"- {tid}:{name}:{unit or 'qualitative'}" for tid, name, unit in tests)
    return LAB_SCAN_PROMPT_TEMPLATE.format(tests=block)
