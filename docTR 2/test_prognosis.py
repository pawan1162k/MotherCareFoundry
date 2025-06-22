from prognosis.llm import process_patient_data
from storage.chroma_db import init_chroma, store_data
import os

def test_prognosis():
    """Test prognosis with sample_blood.pdf OCR output."""
    patient_data = {
        "form_data": {
            "age": 20,
            "gender": "Male",
            "history": "None"
        },
        "symptoms": "Fatigue, mild fever",
        "blood_report": {
            "text": "Name: Mr Dummy\nPatient ID: PN2\nAge/Gender: 20/Male\nReport ID: RE1\nReferred By: Self\nCollection Date: 24/06/2023 08:49 PM\nPhone No.: \nReport Date: 24/06/2023 09:02 PM\nHAEMATOLOGY COMPLETE BLOOD COUNT\n",
            "tables": [
                {"rows": [["Hemoglobin", "13.5 g/dL"], ["WBC", "7.2 x 10^3/uL"]]},
                {"rows": [["Platelets", "250 x 10^3/uL"]]}
            ]
        },
        "scan_report": {}
    }

    collection = init_chroma()
    if collection:
        store_data(collection, "patient_1", patient_data["blood_report"]["text"], {"type": "Blood"})

    result = process_patient_data(patient_data)
    print("Prognosis Result:")
    print(f"Prognosis: {result['prognosis']}")
    print(f"Severity: {result['severity']}")
    print(f"Details: {result['details'][:200]}...")
    return result

if __name__ == "__main__":
    test_prognosis()