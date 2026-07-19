import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.services.post_ocr_corrector import PostOCRCorrector


def run_checks():
    print("=== PostOCR Corrector Tests ===\n")

    # --- Test 1: Exact case from user's issue ---
    print("Test 1: 'Jamil Nadu' + pincode 604208 (Tamil Nadu)")
    fields = {
        "name": "Praveen Rathinam P",
        "state": "Jamil Nadu",        # OCR error: T -> J
        "city": "Peruvalur",
        "pincode": "604208",           # 60xx = Tamil Nadu
        "address": "MARIYAMMAN KOVIL STREET, PERUVALUR, Jamil Nadu 604208"
    }
    corrected = PostOCRCorrector.correct_fields(fields)
    print(f"  state:   '{fields['state']}' -> '{corrected['state']}'")
    print(f"  address: '{corrected['address']}'")
    assert corrected["state"] == "Tamil Nadu", f"FAILED: got {corrected['state']}"
    print("  PASSED\n")

    # --- Test 2: Fuzzy matching alone (no pincode) ---
    print("Test 2: Fuzzy match 'Kamataka' -> 'Karnataka'")
    fields2 = {"state": "Kamataka"}
    c2 = PostOCRCorrector.correct_fields(fields2)
    print(f"  state: '{fields2['state']}' -> '{c2['state']}'")
    assert c2["state"] == "Karnataka", f"FAILED: got {c2['state']}"
    print("  PASSED\n")

    # --- Test 3: Known corrections dict ---
    print("Test 3: Known dict 'tamilnadu' -> 'Tamil Nadu'")
    fields3 = {"state": "tamilnadu"}
    c3 = PostOCRCorrector.correct_fields(fields3)
    print(f"  state: '{fields3['state']}' -> '{c3['state']}'")
    assert c3["state"] == "Tamil Nadu", f"FAILED: got {c3['state']}"
    print("  PASSED\n")

    # --- Test 4: Pincode-only (no state provided) ---
    print("Test 4: Pincode 110001 -> Delhi (no state in fields)")
    fields4 = {"pincode": "110001"}
    c4 = PostOCRCorrector.correct_fields(fields4)
    print(f"  state from pincode 110001: '{c4.get('state')}'")
    assert c4["state"] == "Delhi", f"FAILED: got {c4.get('state')}"
    print("  PASSED\n")

    # --- Test 5: Pincode overrides wrong OCR state ---
    print("Test 5: Pincode 400001 (Maharashtra) overrides OCR 'Maharastra'")
    fields5 = {"state": "Maharastra", "pincode": "400001"}
    c5 = PostOCRCorrector.correct_fields(fields5)
    print(f"  state: '{fields5['state']}' -> '{c5['state']}'")
    assert c5["state"] == "Maharashtra", f"FAILED: got {c5['state']}"
    print("  PASSED\n")

    # --- Test 6: More fuzzy matches ---
    cases = [
        ("Rajastnan",  "Rajasthan"),
        ("West Begal", "West Bengal"),
        ("Gujrat",     "Gujarat"),
        ("Keralaa",    "Kerala"),
    ]
    print("Test 6: Additional fuzzy state matches")
    for raw, expected in cases:
        result = PostOCRCorrector._fuzzy_match_state(raw)
        status = "PASSED" if result == expected else f"FAILED (got {result})"
        print(f"  '{raw}' -> '{result}' [{status}]")

    print("\n=== All Tests Complete ===")


if __name__ == "__main__":
    run_checks()
