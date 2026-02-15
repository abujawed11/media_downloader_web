# Clear Download History API

New API endpoints to manage and clear download history.

## Endpoints Added

### 1. Delete Individual Job
**DELETE** `/jobs/{job_id}?delete_file=false`

Deletes a specific job from history.

**Parameters:**
- `job_id` (path) - The job ID to delete
- `delete_file` (query, optional) - Whether to also delete downloaded files (default: false)

**Example:**
```bash
# Delete job from history only (keep file)
curl -X DELETE http://localhost:8000/jobs/abc-123-def

# Delete job AND downloaded file
curl -X DELETE http://localhost:8000/jobs/abc-123-def?delete_file=true
```

**Response:**
```json
{
  "status": "deleted",
  "job_id": "abc-123-def",
  "file_deleted": false
}
```

---

### 2. Clear All Jobs (Clear History)
**DELETE** `/jobs?delete_files=false`

Clears all jobs from download history.

**Parameters:**
- `delete_files` (query, optional) - Whether to also delete all downloaded files (default: false)

**Example:**
```bash
# Clear history only (keep all files)
curl -X DELETE http://localhost:8000/jobs

# Clear history AND delete all files
curl -X DELETE http://localhost:8000/jobs?delete_files=true
```

**Response:**
```json
{
  "status": "cleared",
  "jobs_deleted": 5,
  "files_deleted": 0
}
```

---

## Frontend Implementation

### React/TypeScript Example

```typescript
// API client functions
const api = {
  /**
   * Delete a single job from history
   */
  deleteJob: async (jobId: string, deleteFile = false) => {
    const response = await fetch(
      `/jobs/${jobId}?delete_file=${deleteFile}`,
      { method: 'DELETE' }
    );
    return response.json();
  },

  /**
   * Clear all download history
   */
  clearAllJobs: async (deleteFiles = false) => {
    const response = await fetch(
      `/jobs?delete_files=${deleteFiles}`,
      { method: 'DELETE' }
    );
    return response.json();
  }
};

// Usage in component
const DownloadHistoryComponent = () => {
  const [jobs, setJobs] = useState([]);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  /**
   * Delete a single job
   */
  const handleDeleteJob = async (jobId: string) => {
    try {
      await api.deleteJob(jobId, false); // Don't delete file
      setJobs(jobs.filter(j => j.id !== jobId));
      toast.success('Job removed from history');
    } catch (error) {
      toast.error('Failed to delete job');
    }
  };

  /**
   * Clear all history with confirmation
   */
  const handleClearAll = async (deleteFiles = false) => {
    // Show confirmation modal first
    const confirmed = await showConfirmDialog({
      title: 'Clear Download History?',
      message: deleteFiles
        ? 'This will delete all jobs AND downloaded files. This cannot be undone.'
        : 'This will clear your download history but keep the files.',
      confirmText: deleteFiles ? 'Delete Everything' : 'Clear History',
      confirmStyle: deleteFiles ? 'danger' : 'primary'
    });

    if (!confirmed) return;

    try {
      const result = await api.clearAllJobs(deleteFiles);
      setJobs([]);
      toast.success(
        `Cleared ${result.jobs_deleted} jobs` +
        (deleteFiles ? ` and deleted ${result.files_deleted} files` : '')
      );
    } catch (error) {
      toast.error('Failed to clear history');
    }
  };

  return (
    <div>
      {/* Clear All Button */}
      <div className="history-header">
        <h2>Download History</h2>
        <div className="actions">
          <button
            onClick={() => handleClearAll(false)}
            className="btn btn-secondary"
          >
            Clear History
          </button>
          <button
            onClick={() => handleClearAll(true)}
            className="btn btn-danger"
          >
            Delete All
          </button>
        </div>
      </div>

      {/* Job List */}
      {jobs.map(job => (
        <div key={job.id} className="job-item">
          <div className="job-info">
            <h3>{job.title}</h3>
            <p>Status: {job.status}</p>
          </div>
          <div className="job-actions">
            {job.status === 'done' && (
              <button onClick={() => downloadFile(job.id)}>
                Download
              </button>
            )}
            <button
              onClick={() => handleDeleteJob(job.id)}
              className="btn-icon"
              title="Remove from history"
            >
              🗑️
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
```

---

## UI/UX Recommendations

### 1. Individual Job Removal
**Location**: On each job card/row

**Options:**
```
┌─────────────────────────────────────┐
│ Video Title                         │
│ Status: Done                        │
│                                     │
│ [Download] [Remove] [⋮]            │
└─────────────────────────────────────┘
```

**Behavior:**
- Single click removes from history (no confirmation needed)
- Optional: Add undo toast notification
- Files are kept by default

---

### 2. Clear All History Button
**Location**: Top of download history page

**Options:**
```
┌──────────────────────────────────────┐
│  Download History           [Clear ▼]│
├──────────────────────────────────────┤
│  Dropdown menu:                      │
│  • Clear History (Keep Files)        │
│  • Delete All (History + Files) ⚠️   │
└──────────────────────────────────────┘
```

**Confirmation Modal:**
```
┌────────────────────────────────────┐
│  Clear Download History?           │
├────────────────────────────────────┤
│  This will remove 15 completed     │
│  downloads from your history.      │
│                                    │
│  Downloaded files will be kept.    │
│                                    │
│  [Cancel] [Clear History]          │
└────────────────────────────────────┘
```

**For "Delete All":**
```
┌────────────────────────────────────┐
│  ⚠️ Delete Everything?             │
├────────────────────────────────────┤
│  This will permanently delete:     │
│  • 15 download jobs                │
│  • All downloaded files (1.2 GB)   │
│                                    │
│  This action cannot be undone!     │
│                                    │
│  Type "DELETE" to confirm:         │
│  [________________]                │
│                                    │
│  [Cancel] [Delete Everything]      │
└────────────────────────────────────┘
```

---

## Advanced: Bulk Selection

```typescript
const DownloadHistoryWithBulkActions = () => {
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [jobs, setJobs] = useState([]);

  const toggleSelectJob = (jobId: string) => {
    const newSelected = new Set(selectedJobs);
    if (newSelected.has(jobId)) {
      newSelected.delete(jobId);
    } else {
      newSelected.add(jobId);
    }
    setSelectedJobs(newSelected);
  };

  const selectAll = () => {
    setSelectedJobs(new Set(jobs.map(j => j.id)));
  };

  const clearSelection = () => {
    setSelectedJobs(new Set());
  };

  const deleteSelected = async () => {
    const confirmed = confirm(
      `Delete ${selectedJobs.size} selected jobs?`
    );
    if (!confirmed) return;

    try {
      // Delete in parallel
      await Promise.all(
        Array.from(selectedJobs).map(id => api.deleteJob(id))
      );

      setJobs(jobs.filter(j => !selectedJobs.has(j.id)));
      setSelectedJobs(new Set());
      toast.success(`Deleted ${selectedJobs.size} jobs`);
    } catch (error) {
      toast.error('Failed to delete some jobs');
    }
  };

  return (
    <div>
      {/* Bulk Actions Bar */}
      {selectedJobs.size > 0 && (
        <div className="bulk-actions-bar">
          <span>{selectedJobs.size} selected</span>
          <button onClick={deleteSelected}>Delete Selected</button>
          <button onClick={clearSelection}>Clear Selection</button>
        </div>
      )}

      {/* Select All Checkbox */}
      <div className="history-header">
        <label>
          <input
            type="checkbox"
            checked={selectedJobs.size === jobs.length}
            onChange={(e) => e.target.checked ? selectAll() : clearSelection()}
          />
          Select All
        </label>
      </div>

      {/* Job List with Checkboxes */}
      {jobs.map(job => (
        <div key={job.id} className="job-item">
          <input
            type="checkbox"
            checked={selectedJobs.has(job.id)}
            onChange={() => toggleSelectJob(job.id)}
          />
          {/* Rest of job card */}
        </div>
      ))}
    </div>
  );
};
```

---

## Testing

### Test Clear History (Keep Files)
```bash
# Start some downloads first
curl -X POST http://localhost:8000/jobs/start \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/video","format":"best","title":"Test"}'

# List jobs
curl http://localhost:8000/jobs

# Clear all history (keep files)
curl -X DELETE http://localhost:8000/jobs

# Verify jobs list is empty
curl http://localhost:8000/jobs
# Should return: []

# Check files still exist
docker exec media-downloader-api ls -la /app/downloads/
# Files should still be there
```

### Test Delete Everything
```bash
# Clear history AND delete files
curl -X DELETE 'http://localhost:8000/jobs?delete_files=true'

# Check files are deleted
docker exec media-downloader-api ls -la /app/downloads/
# Should be empty (or only contain active downloads)
```

### Test Individual Job Deletion
```bash
# Get a job ID
JOB_ID=$(curl -s http://localhost:8000/jobs | jq -r '.[0].id')

# Delete just that job
curl -X DELETE "http://localhost:8000/jobs/$JOB_ID"

# Verify it's gone
curl http://localhost:8000/jobs | grep "$JOB_ID"
# Should not find it
```

---

## Security Considerations

1. **Rate Limiting**: Consider adding rate limits to prevent abuse
2. **Authentication**: Add auth if this is a multi-user system
3. **Confirmation**: Always require explicit user confirmation for destructive actions
4. **Audit Log**: Log deletion events for debugging

---

## Files Modified

✅ `server/app/routers/media.py` - Added delete endpoints
✅ `server/app/services/job_manager.py` - Added delete_job function
✅ `server/app/services/celery_job_manager.py` - Added delete_job function
✅ `server/app/services/hybrid_job_manager.py` - Exported delete_job

---

## Quick Implementation Checklist for Frontend

- [ ] Add "Remove" button to each job card
- [ ] Add "Clear History" button to top of page
- [ ] Implement confirmation modal for "Clear All"
- [ ] Add option: "Clear History" vs "Delete Everything"
- [ ] Show toast notification on success
- [ ] Handle errors gracefully
- [ ] Optional: Add bulk selection/deletion
- [ ] Optional: Add undo functionality
- [ ] Optional: Show storage space saved after deletion

---

**API is ready! Now implement the UI buttons to call these endpoints.**
