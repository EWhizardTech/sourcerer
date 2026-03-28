Implement ONLY folder metadata extraction.

Input:
{
  "file_id": "...",
  "file_name": "...",
  "file_path": "...",
  "provided_metadata": {
    "course_code": "...",
    "year": "..."
  }
}

Requirements:

1. Extract folder segments from file_path:
   Example:
   "/random/CA1/unit2/file.pdf" →
   ["random", "CA1", "unit2"]

2. Remove:
   - empty values
   - file name

3. Normalize:
   - lowercase all tags

4. Treat remaining folder names as tags:
   ["ca1", "unit2"]

5. Merge with provided metadata:

Output:
{
  "file_id": "...",
  "file_name": "...",
  "folder_metadata": {
    "course_code": "...",
    "year": "...",
    "tags": [...]
  }
}

Structure:
- services/metadata_service.py

Function:
- extract_folder_metadata(file_path, provided_metadata)

Constraints:
- Do NOT use LLM
- Deterministic only
- Do NOT infer course_code/year from folders
- Always trust provided metadata

At the end:
- Show example input → output