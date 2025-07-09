import sqlite3

def normalize_denial_category(cat):
    if not cat or str(cat).strip().lower() in {"none", "other", "unclear", ""}:
        return "None"
    mapping = {
        "medical necessity": "Medical Necessity",
        "prior authorization": "Prior Authorization",
        "formulary": "Formulary",
        "coordination of benefits": "Coordination of Benefits",
        "network": "Network",
        "documentation": "Documentation",
        "coverage limits": "Coverage Limits",
        "timing": "Timing",
        "eligibility": "Eligibility"
    }
    cat_clean = str(cat).strip().lower()
    for key in mapping:
        if key in cat_clean:
            return mapping[key]
    return cat_clean.title()

def normalize_db_denial_categories(db_path="analysis.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT thread_id, denial_category FROM thread_analyses")
    updates = []
    for thread_id, cat in cur.fetchall():
        norm = normalize_denial_category(cat)
        if norm != cat:
            updates.append((norm, thread_id))
    print(f"Normalizing {len(updates)} records...")
    cur.executemany("UPDATE thread_analyses SET denial_category=? WHERE thread_id=?", updates)
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    normalize_db_denial_categories()