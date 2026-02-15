# Frontend: Add Remove Button to Download Cards

## What You Need

Add a **remove button (❌ or 🗑️)** to each download card so users can clear it from the history.

---

## Quick Implementation

### 1. Add Remove Button to Each Card

```tsx
// In your DownloadCard component or wherever you render each download

interface DownloadCardProps {
  job: Job;
  onRemove: (jobId: string) => void;  // Add this callback
}

const DownloadCard = ({ job, onRemove }: DownloadCardProps) => {
  return (
    <div className="download-card">
      {/* Existing card content */}
      <div className="card-header">
        <h3>{job.title}</h3>

        {/* Add remove button here */}
        <button
          onClick={() => onRemove(job.id)}
          className="btn-remove"
          title="Remove from history"
          aria-label="Remove"
        >
          ❌
          {/* Or use an icon: */}
          {/* <TrashIcon /> */}
        </button>
      </div>

      <div className="card-body">
        <p>Status: {job.status}</p>
        <progress value={job.progress} max={1} />

        {/* Download button for completed */}
        {job.status === 'done' && (
          <button onClick={() => downloadFile(job.id)}>
            Download
          </button>
        )}

        {/* Error message */}
        {job.status === 'error' && (
          <p className="error">{job.error}</p>
        )}
      </div>
    </div>
  );
};
```

---

### 2. Implement Remove Function in Parent Component

```tsx
// In your main component that manages the download list

const DownloadsPage = () => {
  const [jobs, setJobs] = useState<Job[]>([]);

  /**
   * Remove a job from the UI (calls the API)
   */
  const handleRemoveJob = async (jobId: string) => {
    try {
      // Call the DELETE endpoint (keeps the file)
      const response = await fetch(`/jobs/${jobId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to remove job');
      }

      // Remove from UI immediately
      setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));

      // Optional: Show success toast
      // toast.success('Removed from history');

    } catch (error) {
      console.error('Error removing job:', error);
      // toast.error('Failed to remove job');
    }
  };

  return (
    <div className="downloads-page">
      <h1>Downloads</h1>

      {/* Render all download cards */}
      {jobs.map(job => (
        <DownloadCard
          key={job.id}
          job={job}
          onRemove={handleRemoveJob}  // Pass the remove handler
        />
      ))}

      {jobs.length === 0 && (
        <p className="empty-state">No downloads yet</p>
      )}
    </div>
  );
};
```

---

### 3. Add "Clear All History" Button (Optional)

```tsx
const DownloadsPage = () => {
  const [jobs, setJobs] = useState<Job[]>([]);

  const handleRemoveJob = async (jobId: string) => {
    // ... (same as above)
  };

  /**
   * Clear all completed/error jobs from history
   */
  const handleClearHistory = async () => {
    // Confirm with user first
    const confirmed = window.confirm(
      'Clear all download history? (Files will not be deleted)'
    );
    if (!confirmed) return;

    try {
      // Call the DELETE /jobs endpoint
      const response = await fetch('/jobs', {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to clear history');
      }

      // Clear the UI
      setJobs([]);

      // Optional: Show success message
      // toast.success('History cleared');

    } catch (error) {
      console.error('Error clearing history:', error);
      // toast.error('Failed to clear history');
    }
  };

  // Only show "clear" button if there are completed/error jobs
  const hasCompletedOrErrorJobs = jobs.some(
    job => job.status === 'done' || job.status === 'error'
  );

  return (
    <div className="downloads-page">
      <div className="page-header">
        <h1>Downloads</h1>

        {/* Clear All Button */}
        {hasCompletedOrErrorJobs && (
          <button
            onClick={handleClearHistory}
            className="btn-clear-all"
          >
            Clear History
          </button>
        )}
      </div>

      {/* Download cards */}
      {jobs.map(job => (
        <DownloadCard
          key={job.id}
          job={job}
          onRemove={handleRemoveJob}
        />
      ))}
    </div>
  );
};
```

---

## CSS Styling

### For the Remove Button (❌)

```css
/* Remove button on card */
.download-card {
  position: relative;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.btn-remove {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 18px;
  opacity: 0.6;
  transition: opacity 0.2s, transform 0.2s;
  padding: 4px 8px;
}

.btn-remove:hover {
  opacity: 1;
  transform: scale(1.1);
}

.btn-remove:active {
  transform: scale(0.95);
}

/* Alternative: Use icon in a circle */
.btn-remove-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f0f0f0;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.btn-remove-circle:hover {
  background: #ff4444;
  color: white;
}
```

### For the Clear All Button

```css
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.btn-clear-all {
  padding: 8px 16px;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-clear-all:hover {
  background: #e0e0e0;
  border-color: #999;
}
```

---

## Advanced: Only Show Remove for Completed/Error Jobs

```tsx
const DownloadCard = ({ job, onRemove }: DownloadCardProps) => {
  // Only show remove button for completed or error jobs
  const canRemove = job.status === 'done' || job.status === 'error';

  return (
    <div className="download-card">
      <div className="card-header">
        <h3>{job.title}</h3>

        {/* Only show remove if job is done/error */}
        {canRemove && (
          <button
            onClick={() => onRemove(job.id)}
            className="btn-remove"
            title="Remove from history"
          >
            ❌
          </button>
        )}
      </div>

      {/* Rest of card... */}
    </div>
  );
};
```

---

## Better UX: Add Animation on Remove

```tsx
import { useState } from 'react';

const DownloadCard = ({ job, onRemove }: DownloadCardProps) => {
  const [isRemoving, setIsRemoving] = useState(false);

  const handleRemove = async () => {
    // Start fade-out animation
    setIsRemoving(true);

    // Wait for animation to complete
    setTimeout(async () => {
      await onRemove(job.id);
    }, 300);
  };

  return (
    <div
      className={`download-card ${isRemoving ? 'removing' : ''}`}
    >
      {/* Card content */}
      <button onClick={handleRemove}>❌</button>
    </div>
  );
};
```

```css
.download-card {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.download-card.removing {
  opacity: 0;
  transform: translateX(100%);
}
```

---

## Complete Example (Copy-Paste Ready)

```tsx
import React, { useState } from 'react';
import './Downloads.css';

interface Job {
  id: string;
  title: string;
  status: 'queued' | 'downloading' | 'done' | 'error' | 'paused';
  progress: number;
  error?: string;
}

interface DownloadCardProps {
  job: Job;
  onRemove: (jobId: string) => void;
  onDownload: (jobId: string) => void;
}

const DownloadCard: React.FC<DownloadCardProps> = ({ job, onRemove, onDownload }) => {
  const [isRemoving, setIsRemoving] = useState(false);
  const canRemove = job.status === 'done' || job.status === 'error';

  const handleRemove = () => {
    setIsRemoving(true);
    setTimeout(() => onRemove(job.id), 300);
  };

  return (
    <div className={`download-card ${isRemoving ? 'removing' : ''}`}>
      <div className="card-header">
        <h3 className="card-title">{job.title}</h3>
        {canRemove && (
          <button
            onClick={handleRemove}
            className="btn-remove"
            title="Remove from history"
            aria-label="Remove"
          >
            ❌
          </button>
        )}
      </div>

      <div className="card-body">
        <div className="status">
          Status: <span className={`status-${job.status}`}>{job.status}</span>
        </div>

        {job.status === 'downloading' && (
          <progress value={job.progress} max={1} className="progress-bar" />
        )}

        {job.status === 'done' && (
          <button
            onClick={() => onDownload(job.id)}
            className="btn-download"
          >
            📥 Download
          </button>
        )}

        {job.status === 'error' && (
          <p className="error-message">{job.error}</p>
        )}
      </div>
    </div>
  );
};

export const DownloadsPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);

  const handleRemoveJob = async (jobId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/jobs/${jobId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to remove');

      setJobs(prev => prev.filter(job => job.id !== jobId));
    } catch (error) {
      console.error('Remove failed:', error);
      alert('Failed to remove job');
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Clear all history? (Files will not be deleted)')) {
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/jobs', {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to clear');

      setJobs([]);
    } catch (error) {
      console.error('Clear failed:', error);
      alert('Failed to clear history');
    }
  };

  const handleDownload = (jobId: string) => {
    window.location.href = `http://localhost:8000/jobs/${jobId}/file`;
  };

  const hasCompletedJobs = jobs.some(
    job => job.status === 'done' || job.status === 'error'
  );

  return (
    <div className="downloads-page">
      <div className="page-header">
        <h1>Downloads</h1>
        {hasCompletedJobs && (
          <button onClick={handleClearAll} className="btn-clear-all">
            🗑️ Clear History
          </button>
        )}
      </div>

      <div className="downloads-list">
        {jobs.map(job => (
          <DownloadCard
            key={job.id}
            job={job}
            onRemove={handleRemoveJob}
            onDownload={handleDownload}
          />
        ))}

        {jobs.length === 0 && (
          <div className="empty-state">
            <p>No downloads yet</p>
          </div>
        )}
      </div>
    </div>
  );
};
```

---

## Summary

**What you need to add to your frontend:**

1. ✅ **Remove button (❌)** on each download card
2. ✅ **`onClick` handler** that calls `DELETE /jobs/{job_id}`
3. ✅ **Update state** to remove the card from UI
4. ✅ **Optional: "Clear All" button** that calls `DELETE /jobs`

**The backend API is already ready!** Just add these UI buttons and they'll work immediately.

---

## Testing

1. Start a download
2. Wait for it to complete
3. Click the ❌ button
4. Card should disappear from UI
5. File still exists in `/app/downloads/`
6. Click "Clear History" to remove all cards

**Ready to implement!** 🚀
