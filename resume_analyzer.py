from google import genai
from google.genai import types
import pathlib
import gradio as gr
import pandas as pd

client = genai.Client()

schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "full_name": types.Schema(type=types.Type.STRING),
        "match_score": types.Schema(type=types.Type.INTEGER, description="score from 0-100 indicating how well the resume matches role."),
        "summary": types.Schema(type=types.Type.STRING),
        "experience_highlights": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="if none, return NA"),
        "matching_skills": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="if none, return NA"),
        "missing_skills": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="if none, return NA"),
        "suggested_questions": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="one question"),
    },
    required=["full_name", "match_score", "summary", "experience_highlights", "matching_skills", "missing_skills", "suggested_questions"]
)

tool = types.Tool(function_declarations=[types.FunctionDeclaration(name="analyze_resume", parameters=schema)])

rankings = {}  # Changed from list to dictionary

def get_rankings_for_role(job_role):
    """Get rankings for a specific role"""
    return rankings.get(job_role, [])

def analyze_resume(file, job_role):
    if file is None:
        return pd.DataFrame(), [], job_role
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Part.from_bytes(data=pathlib.Path(file.name).read_bytes(), mime_type='application/pdf'),
                      f"Analyze this resume for a {job_role} position using analyze_resume function."],
            config=types.GenerateContentConfig(tools=[tool], tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY", allowed_function_names=["analyze_resume"])))
        )
        
        result = dict(response.candidates[0].content.parts[0].function_call.args)
        
        # Create separate rankings for each job role
        if job_role not in rankings:
            rankings[job_role] = []
        
        rankings[job_role].append([result['full_name'], result['match_score']])
        rankings[job_role].sort(key=lambda x: x[1], reverse=True)
        
        details_data = [
            ["Full Name", result['full_name']],
            ["Score", f"{result['match_score']}/100"],
            ["Summary", result['summary']],
            ["Experience Highlights", "\n".join(f"{exp}" for exp in result['experience_highlights'])],
            ["Matching Skills", ", ".join(result['matching_skills'])],
            ["Missing Skills", ", ".join(result['missing_skills'])],
            ["Questions", "\n".join(f"{i+1}. {q}" for i, q in enumerate(result['suggested_questions']))]
        ]
        
        details_df = pd.DataFrame(details_data, columns=["Field", "Value"])
        
        # Return the job_role as well to update the dropdown
        return details_df, rankings[job_role], job_role
    
    except Exception as e:
        current_rankings = rankings.get(job_role, [])
        return pd.DataFrame([["Error", str(e)]], columns=["Field", "Value"]), current_rankings, job_role
        
my_theme = gr.Theme.from_hub("gstaff/sketch") #shivi/calm_seafoam

with gr.Blocks(theme=my_theme) as app:
#with gr.Blocks(theme=gr.themes.Soft()) as app:
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
                value=[]
            )
    
    analyze_btn.click(
        analyze_resume, 
        inputs=[file_input, job_dropdown], 
        outputs=[result_table, ranking_table, view_role_dropdown]
    )
    view_role_dropdown.change(get_rankings_for_role, inputs=[view_role_dropdown], outputs=[ranking_table])

app.launch()
