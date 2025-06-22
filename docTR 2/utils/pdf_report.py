import os
from huggingface_hub import InferenceClient
from typing import Dict
import tempfile
import subprocess
import shutil
import re


PDFLATEX_PATH = r"/opt/homebrew/bin/pdflatex"

def parse_macro_breakdown(macro_text: str) -> dict:
    """Parse macro breakdown from text with robust error handling"""
    if not macro_text:
        return {}
    
    macros = {}
    patterns = {
        "protein": r"Protein:? ([\d.]+)g?.*?\(([\d.]+)%",
        "carbs": r"Carbs:? ([\d.]+)g?.*?\(([\d.]+)%",
        "fats": r"Fats:? ([\d.]+)g?.*?\(([\d.]+)%"
    }
    
    for key, pattern in patterns.items():
        try:
            match = re.search(pattern, macro_text, re.IGNORECASE)
            if match:
                macros[f"{key}_grams"] = float(match.group(1))
                macros[f"{key}_percent"] = float(match.group(2))
        except Exception:
            pass
    
    return macros

def generate_latex_report_with_llm(patient_data: Dict, health_recommendation: Dict) -> str:
    # Parse macros if available
    macros = {}
    if "macro_breakdown" in health_recommendation:
        macro_text = health_recommendation["macro_breakdown"]
        if macro_text:
            macros = parse_macro_breakdown(macro_text)
    
    # Calculate BMI
    form = patient_data["form_data"]
    height = form.get("height", 1.7)
    weight = form.get("weight", 70)
    bmi = weight / (height ** 2) if height > 0 else 0
    
    # Get weight status
    if bmi < 18.5:
        weight_status = "Underweight"
    elif 18.5 <= bmi < 25:
        weight_status = "Normal weight"
    elif 25 <= bmi < 30:
        weight_status = "Overweight"
    else:
        weight_status = "Obese"
    
    # Format meal plan
    meal_plan = health_recommendation.get("meal_plan", "")
    formatted_meal_plan = ""
    if meal_plan:
        # Split into days
        days = re.split(r"Day \d+:", meal_plan)
        for i, day in enumerate(days[1:], 1):
            formatted_meal_plan += f"\\subsection*{{Day {i}}}\n"
            meals = [m.strip() for m in day.split("\n") if m.strip()]
            for meal in meals:
                formatted_meal_plan += f"\\begin{{itemize}}\n  \\item {meal}\n\\end{{itemize}}\n"
    
    # Format grocery list
    grocery_list = health_recommendation.get("grocery_list", "")
    formatted_grocery_list = ""
    if grocery_list:
        items = [item.strip() for item in grocery_list.split("\n") if item.strip()]
        formatted_grocery_list = "\\begin{itemize}\n"
        for item in items:
            formatted_grocery_list += f"  \\item {item}\n"
        formatted_grocery_list += "\\end{itemize}"
    
    # Create LaTeX template
    latex_template = f"""
\\documentclass{{article}}
\\usepackage{{xcolor}}
\\usepackage{{tcolorbox}}
\\tcbuselibrary{{breakable}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{enumitem}}
\\usepackage{{hyperref}}
\\hypersetup{{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,      
    urlcolor=cyan,
}}

\\title{{Health \\& Nutrition Plan}}
\\date{{\\today}}
\\author{{MedDoc AI}}

\\begin{{document}}

\\maketitle

\\section*{{Patient Information}}
\\begin{{itemize}}[leftmargin=*]
    \\item \\textbf{{Name}}: {form.get('full_name', 'N/A')}
    \\item \\textbf{{Age}}: {form.get('age', 'N/A')}
    \\item \\textbf{{Gender}}: {form.get('gender', 'N/A')}
    \\item \\textbf{{Phone}}: {form.get('phone', 'N/A')}
    \\item \\textbf{{Email}}: {form.get('email', 'N/A')}
    \\item \\textbf{{Blood Group}}: {form.get('blood_group', 'N/A')}
    \\item \\textbf{{Medical History}}: {form.get('history', 'N/A')}
\\end{{itemize}}

\\section*{{Health Summary}}
\\begin{{itemize}}[leftmargin=*]
    \\item \\textbf{{BMI}}: {bmi:.1f} ({weight_status})
    \\item \\textbf{{Current Weight}}: {weight:.1f} kg
    \\item \\textbf{{Target Weight}}: {patient_data['goal'].get('target_weight', 'N/A')} kg
    \\item \\textbf{{Goal}}: {patient_data['goal'].get('description', 'N/A')}
\\end{{itemize}}

\\section*{{Nutrition Plan}}
\\subsection*{{Daily Calorie Target}}
{health_recommendation.get('calorie_target', 'N/A')} kcal

\\subsection*{{Macronutrient Breakdown}}
\\begin{{itemize}}[leftmargin=*]
    \\item \\textbf{{Protein}}: {macros.get('protein_grams', 0):.0f}g ({macros.get('protein_percent', 0):.0f}\\% of calories)
    \\item \\textbf{{Carbohydrates}}: {macros.get('carbs_grams', 0):.0f}g ({macros.get('carbs_percent', 0):.0f}\\% of calories)
    \\item \\textbf{{Fats}}: {macros.get('fats_grams', 0):.0f}g ({macros.get('fats_percent', 0):.0f}\\% of calories)
\\end{{itemize}}

\\subsection*{{Nutrition Guidance}}
{health_recommendation.get('nutrition_guidance', 'No guidance available')}

\\section*{{3-Day Meal Plan}}
{formatted_meal_plan}

\\section*{{Grocery List}}
{formatted_grocery_list}

\\section*{{Additional Recommendations}}
\\begin{{tcolorbox}}[colback=blue!5!white,colframe=blue!75!black,title=Doctor Consultation]
{health_recommendation.get('doctor_recommendation', 'No additional recommendations at this time.')}
\\end{{tcolorbox}}

\\vspace*{{\\fill}}
\\begin{{center}}
    \\small \\textit{{Generated by MedDoc AI}} \\\\
    \\footnotesize \\textcolor{{gray}}{{This health recommendation is AI-generated and should be verified by a professional.}}
\\end{{center}}

\\end{{document}}
"""

    return latex_template

def create_pdf_report(patient_data: Dict, health_recommendation: Dict) -> str:
    latex_code = generate_latex_report_with_llm(patient_data, health_recommendation)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "report.tex")
        pdf_path = os.path.join(tmpdir, "report.pdf")
        
        # Save LaTeX
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_code)

        # Compile PDF using pdflatex (run twice to resolve references)
        subprocess.run([PDFLATEX_PATH, "-output-directory", tmpdir, tex_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([PDFLATEX_PATH, "-output-directory", tmpdir, tex_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        final_path = os.path.join(os.getcwd(), "health_plan.pdf")
        if os.path.exists(pdf_path):
            shutil.copy(pdf_path, final_path)
        else:
            # Fallback: Return the LaTeX code if PDF generation fails
            with open(final_path + ".tex", "w", encoding="utf-8") as f:
                f.write(latex_code)
            return final_path + ".tex"

    return final_path