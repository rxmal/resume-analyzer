from google import genai
from google.genai import types
import pathlib

client = genai.Client()

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

def analyze_resume_with_gemini(file, job_role):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_bytes(data=pathlib.Path(file.name).read_bytes(), mime_type='application/pdf'),
                  f"Analyze this resume for a {job_role} position using analyze_resume function."],
        config=types.GenerateContentConfig(tools=[tool], tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY", allowed_function_names=["analyze_resume"])))
    )
    
    result = dict(response.candidates[0].content.parts[0].function_call.args)
    return result