Implement folder metadata extraction from Google Drive file paths.

Input:
- File metadata from GDrive:
  - file_name
  - file_id
  - full_path (e.g., /CS101/2023/Midterm/file.pdf)

Requirements:

1. Parse folder structure into metadata:
   Example:
   /CS101/2023/Midterm/file.pdf →

   {
     "course_code": "CS101",
     "year": "2023",
     "exam_type": "Midterm"
   }

2. Make mapping configurable:
   - Allow defining folder depth meaning:
     level_1 → course_code
     level_2 → year
     level_3 → exam_type

3. Output:
{
  "file_id": "...",
  "file_name": "...",
  "folder_metadata": {
    "course_code": "...",
    "year": "...",
    "exam_type": "..."
  }
}

Structure:
- services/metadata_service.py

Function:
- extract_folder_metadata(file_path)

Constraints:
- Do NOT use LLM
- Deterministic logic only

At the end:
- Show example input → output

Implement ONLY folder metadata extraction.

Input:
file_path like:
"/CS101/2023/Midterm/file.pdf"

Output:
{
  "course_code": "CS101",
  "year": "2023",
  "exam_type": "midterm"
}

Requirements:
- Configurable folder levels
- Normalize values (lowercase exam_type)

Structure:
- services/metadata_service.py

Function:
- extract_folder_metadata(file_path)

Constraints:
- No LLM
- Deterministic only

At the end:
- Show example