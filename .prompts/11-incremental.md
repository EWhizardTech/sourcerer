Implement incremental processing control.

Input:
{
  "file_id": "...",
  "file_name": "...",
  "file_path": "...",
  "modified_time": "...",
  "content": bytes
}

Requirements:

1. Compute file hash:
   - Use MD5 on raw file content

2. Maintain tracking store:
{
  "file_id": "...",
  "file_hash": "...",
  "last_processed_at": "..."
}

3. Determine file status:
   - NEW → file_id not found
   - SKIP → hash unchanged
   - UPDATE → hash changed

4. Behavior:
   - NEW → allow processing
   - SKIP → stop pipeline for this file
   - UPDATE:
       - delete existing vectors from Qdrant using file_id
       - allow reprocessing

5. Qdrant deletion:
   - Use filter:
     file_id == <file_id>

Output:
{
  "status": "NEW" | "SKIP" | "UPDATE"
}

Structure:
- services/incremental_service.py

Functions:
- compute_hash(content)
- check_file_status(file_id, file_hash)
- delete_existing_vectors(file_id)

Constraints:
- Do NOT perform parsing here
- Must integrate with Qdrant deletion
- Must update tracking store after successful processing

At the end:
- Show flow:
  NEW → processed
  SKIP → ignored
  UPDATE → delete + reprocess