from google import genai
from google.genai import types
import pathlib
import gradio as gr
import pandas as pd
import sqlite3
from datetime import datetime

client = genai.Client()

# Database setup
def init_db():
    """Initialize the SQLite database"""
    conn = sqlite3.connect('resume_ranker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            job_role TEXT NOT NULL,
            match_score INTEGER NOT NULL,
            summary TEXT,
            experience_highlights TEXT,
            matching_skills TEXT,
            missing_skills TEXT,
            suggested_questions TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(full_name, job_role)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_to_db(result, job_role):
    """Save resume analysis to database"""
    conn = sqlite3.connect('resume_ranker.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO resumes 
            (full_name, job_role, match_score, summary, experience_highlights, 
             matching_skills, missing_skills, suggested_questions, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['full_name'],
            job_role,
            result['match_score'],
            result['summary'],
            '\n'.join(result['experience_highlights']),
            ', '.join(result['matching_skills']),
            ', '.join(result['missing_skills']),
            '\n'.join(result['suggested_questions']),
            datetime.now()
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def get_rankings_from_db(job_role):
    """Get rankings for a specific role from database"""
    conn = sqlite3.connect('resume_ranker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT full_name, match_score 
        FROM resumes 
        WHERE job_role = ?
        ORDER BY match_score DESC
    ''', (job_role,))
    
    rankings = cursor.fetchall()
    conn.close()
    
    return rankings

def get_all_candidates():
    """Get all candidates from database"""
    conn = sqlite3.connect('resume_ranker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT full_name, job_role, match_score, uploaded_at
        FROM resumes 
        ORDER BY uploaded_at DESC
    ''')
    
    candidates = cursor.fetchall()
    conn.close()
    
    return candidates

def get_candidate_details(name, job_role):
    """Get detailed information for a specific candidate"""
    conn = sqlite3.connect('resume_ranker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM resumes 
        WHERE full_name = ? AND job_role = ?
    ''', (name, job_role))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "full_name": types.Schema(type=types.Type.STRING),
        "match_score": types.Schema(type=types.Type.INTEGER, description="score from 0-100 indicating how well the resume matches role."),
        "summary": types.Schema(type=types.Type.STRING),
        "experience_highlights": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="if none mentioned, return NA"),
        "matching_skills": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="if none mentioned, return NA"),
        "missing_skills": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="if none mentioned, return NA"),
        "suggested_questions": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="one question"),
    },
    required=["full_name", "match_score", "summary", "experience_highlights", "matching_skills", "missing_skills", "suggested_questions"]
)

tool = types.Tool(function_declarations=[types.FunctionDeclaration(name="analyze_resume", parameters=schema)])

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
        
        # Save to database
        save_to_db(result, job_role)
        
        # Get updated rankings from database
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
    """Display all candidates in database"""
    candidates = get_all_candidates()
    if not candidates:
        return pd.DataFrame(columns=["Name", "Job Role", "Score", "Uploaded At"])
    
    df = pd.DataFrame(candidates, columns=["Name", "Job Role", "Score", "Uploaded At"])
    return df

# Initialize database on startup
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

    # Keep your button bindings
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
    
    # Load initial rankings on startup
    app.load(
        lambda: get_rankings_from_db("Software Engineer"),
        outputs=[ranking_table]
    )

app.launch()

