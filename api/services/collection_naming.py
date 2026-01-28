from __future__ import annotations


def sector_to_ai_collection(sector_name: str) -> str:
    sector_lower = (sector_name or "").lower().strip()

    sector_mapping = {
        "technology": "tech_ai_filter",
        "tech": "tech_ai_filter",
        "bt": "tech_ai_filter",
        "bilgi teknolojisi": "tech_ai_filter",
        "finance": "finance_ai_filter",
        "finans": "finance_ai_filter",
        "healthcare": "healthcare_ai_filter",
        "sağlık": "healthcare_ai_filter",
        "manufacturing": "manufacturing_ai_filter",
        "imalat": "manufacturing_ai_filter",
        "retail": "retail_ai_filter",
        "perakende": "retail_ai_filter",
        "education": "education_ai_filter",
        "eğitim": "education_ai_filter",
    }

    if sector_lower in sector_mapping:
        return sector_mapping[sector_lower]

    collection_name = sector_lower.replace(" ", "_").replace("-", "_")
    turkish_chars = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c", "İ": "i"}
    for turkish, english in turkish_chars.items():
        collection_name = collection_name.replace(turkish, english)

    return f"{collection_name}_ai_filter"

