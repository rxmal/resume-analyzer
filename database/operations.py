import sqlite3
from datetime import datetime

def init_db():
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
    conn = sqlite3.connect('resume_ranker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM resumes 
        WHERE full_name = ? AND job_role = ?
    ''', (name, job_role))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def clear_resumes_table():
    conn = sqlite3.connect('resume_ranker.db')
    try:
        conn.execute("DELETE FROM resumes")
        conn.commit()
        print("Table 'resumes' has been cleared.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()
