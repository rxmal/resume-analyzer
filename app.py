import gradio as gr
import pandas as pd
from database.operations import init_db, save_to_db, get_rankings_from_db, get_all_candidates
from services.gemini_service import analyze_resume_with_gemini

def analyze_resume(file, job_role):
    if file is None:
        return pd.DataFrame(), [], job_role
    
    try:
        result = analyze_resume_with_gemini(file, job_role)
        
        save_to_db(result, job_role)
        
        current_rankings = get_rankings_from_db(job_role)
        
        details_data = [
            ["Full Name", result['full_name']],
            ["Score", f"{result['match_score']}/100"],
            ["Summary", result['summary']],
            ["Experience", "\n".join(f"{exp}" for exp in result['experience_highlights'])],
            ["Matching Skills", ", ".join(result['matching_skills'])],
            ["Missing Skills", ", ".join(result['missing_skills'])],
            ["Questions", "\n".join(f"{i+1}. {q}" for i, q in enumerate(result['suggested_questions']))]
        ]
        
        details_df = pd.DataFrame(details_data, columns=["Field", "Value"])
        
        return details_df, current_rankings, job_role
    
    except Exception as e:
        current_rankings = get_rankings_from_db(job_role)
        return pd.DataFrame([["Error", str(e)]], columns=["Field", "Value"]), current_rankings, job_role

def view_all_candidates():
    candidates = get_all_candidates()
    if not candidates:
        return pd.DataFrame(columns=["Name", "Job Role", "Score", "Uploaded At"])
    
    df = pd.DataFrame(candidates, columns=["Name", "Job Role", "Score", "Uploaded At"])
    return df

init_db()

my_theme = gr.Theme.from_hub("gstaff/sketch")

with gr.Blocks(theme=my_theme) as app:
    gr.Markdown("# Resume Ranker")
    gr.Markdown("---")
    
    with gr.Row():
        with gr.Column(scale=2):
            job_dropdown = gr.Dropdown(
                choices=[
                    "Software Engineer",
                    "Intern (Software Engineer)",
                ],
                value="Software Engineer",
                label="Select Job Role"
            )
            file_input = gr.File(label="Upload Resume (PDF)", file_types=[".pdf"])
            analyze_btn = gr.Button("Analyze Resume")
            result_table = gr.Dataframe(
                headers=["Field", "Value"],
                datatype=["str", "str"],
                wrap=True
            )

        with gr.Column(scale=1):
            gr.Markdown("## Rankings")
            view_role_dropdown = gr.Dropdown(
                choices=[
                    "Software Engineer",
                    "Intern (Software Engineer)",
                ],
                value="Software Engineer",
                label="View Rankings For"
            )
            ranking_table = gr.Dataframe(
                headers=["Name", "Score"],
                datatype=["str", "number"],
                value=get_rankings_from_db("Software Engineer")
            )

    analyze_btn.click(
        analyze_resume, 
        inputs=[file_input, job_dropdown], 
        outputs=[result_table, ranking_table, view_role_dropdown]
    )
    
    view_role_dropdown.change(
        get_rankings_from_db, 
        inputs=[view_role_dropdown], 
        outputs=[ranking_table]
    )
    
    app.load(
        lambda: get_rankings_from_db("Software Engineer"),
        outputs=[ranking_table]
    )

app.launch()