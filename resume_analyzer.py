from google import genai
from google.genai import types
import pathlib

client = genai.Client()

schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "full_name": types.Schema(type=types.Type.STRING),
        "match_score": types.Schema(type=types.Type.INTEGER),
        "summary": types.Schema(type=types.Type.STRING),
        "experience_highlights": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "matching_skills": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "missing_skills": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "suggested_questions": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING))
    },
    required=["full_name", "match_score", "summary", "experience_highlights", "matching_skills", "missing_skills", "suggested_questions"]
)

tool = types.Tool(function_declarations=[types.FunctionDeclaration(name="analyze_resume", parameters=schema)])

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[types.Part.from_bytes(data=pathlib.Path('docs/file.pdf').read_bytes(), mime_type='application/pdf'),
              "Analyze this resume for a senior software engineer position using analyze_resume function."],
    config=types.GenerateContentConfig(tools=[tool], tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(mode="ANY", allowed_function_names=["analyze_resume"])))
)

result = dict(response.candidates[0].content.parts[0].function_call.args)

print(f"Full Name: {result['full_name']}\nMatch Score: {result['match_score']}/100\n\nSummary: {result['summary']}\n\nExperience Highlights:")
for exp in result['experience_highlights']: print(f"{exp}")
print("\nMatching Skills:")
for skill in result['matching_skills']: print(f"{skill}")
print("\nMissing Skills:")
for skill in result['missing_skills']: print(f"{skill}")
print("\nSuggested Questions:")
for i, q in enumerate(result['suggested_questions'], 1): print(f"  {i}. {q}")

