import re

CATEGORY_MAP = {
    "makan": ["makan", "sarapan", "lunch", "dinner", "kopi", "jajan"],
    "transport": ["bensin", "grab", "gojek", "ojek", "transport", "tj", "mrt", "krl", "lrt"],
    "belanja": ["belanja", "shopping", "market"],
    "hiburan": ["nonton", "movie", "game"],
}


def parse_message(text: str):
    text_lower = text.lower()

    # amount
    amount_match = re.findall(r"\d+[.,]?\d*[k]?", text_lower)
    if not amount_match:
        return None

    raw_amount = amount_match[-1]

    if raw_amount.endswith("k"):
        amount = int(float(raw_amount[:-1].replace(",", ".")) * 1000)
    else:
        amount = int(raw_amount.replace(".", "").replace(",", ""))

    # type
    tx_type = "income" if any(k in text_lower for k in ["gaji", "salary", "masuk"]) else "expense"

    # category
    category = "other"
    for cat, keywords in CATEGORY_MAP.items():
        if any(k in text_lower for k in keywords):
            category = cat
            break

    return {
        "type": tx_type,
        "category": category,
        "amount": amount,
        "note": text,
    }
