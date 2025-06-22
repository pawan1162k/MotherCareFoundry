def combine_context(form_data, symptoms, report_text, image_labels):
    """Combine patient inputs into a single context string."""
    context = f"Patient Info: {form_data}\nSymptoms: {symptoms}\nReport: {report_text}\nImage Labels: {image_labels}"
    return context

def clean_text(text):
    """Clean extracted text (e.g., remove extra whitespace)."""
    return " ".join(text.strip().split())