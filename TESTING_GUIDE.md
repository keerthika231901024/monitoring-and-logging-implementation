# File Monitoring System - Testing Guide

## Overview
The Flask File Monitoring System now detects ALL file system events in real-time using Python's watchdog library.

## Detected Events

### 1. **File Created** (on_created)
**Triggered when:** A new file is created in the monitored folder

**How to test:**
```
1. Start monitoring a folder (e.g., C:\Users\YourName\Desktop\TestFolder)
2. Create a new text file: Right-click → New → Text Document
3. Check dashboard - should show "● Created" event
```

**Database entry:**
- action: `file_created`
- message: "File created: [path]"
- status: success

---

### 2. **File Deleted** (on_deleted)
**Triggered when:** A file is deleted from the monitored folder

**How to test:**
```
1. Delete an existing file in the monitored folder
2. Check dashboard - should show "● Deleted" event
```

**Database entry:**
- action: `file_deleted`
- message: "File deleted: [path]"
- status: success

---

### 3. **File Modified** (on_modified)
**Triggered when:** File content is changed

**How to test:**
```
1. Open a text file in the monitored folder
2. Add some text and save
3. Check dashboard - should show "● Modified" event
```

**Note:** Modified events are debounced (2-second cooldown) to prevent spam, as watchdog can trigger multiple modify events for a single save operation.

**Database entry:**
- action: `file_modified`
- message: "File modified: [path]"
- status: success

---

### 4. **File Renamed/Moved** (on_moved)
**Triggered when:** A file is renamed or moved within the monitored folder

**How to test:**
```
1. Right-click a file → Rename
2. Change the name and press Enter
3. Check dashboard - should show "● Renamed" event
```

**Database entry:**
- action: `file_renamed`
- message: "File renamed/moved from [old_path] to [new_path]"
- status: success

---

## Complete Test Scenario

### Step 1: Start Monitoring
1. Login to http://127.0.0.1:5000
2. Go to Dashboard
3. Enter folder path: `C:\Users\YourName\Desktop\TestMonitor`
4. Click "Start Monitoring"
5. Status should show "Running"

### Step 2: Create Test Folder
```powershell
mkdir C:\Users\YourName\Desktop\TestMonitor
cd C:\Users\YourName\Desktop\TestMonitor
```

### Step 3: Test All Events
```powershell
# Test 1: Create file
echo "Hello World" > test1.txt
# → Dashboard shows "● Created" for test1.txt

# Test 2: Modify file
echo "More content" >> test1.txt
# → Dashboard shows "● Modified" for test1.txt

# Test 3: Rename file
Rename-Item test1.txt test_renamed.txt
# → Dashboard shows "● Renamed" event

# Test 4: Create another file
echo "Test 2" > test2.txt
# → Dashboard shows "● Created" for test2.txt

# Test 5: Delete file
Remove-Item test2.txt
# → Dashboard shows "● Deleted" for test2.txt
```

### Step 4: Verify Results
1. Check "Live File Changes" section on Dashboard
2. Should see 5 events:
   - ● Created (test1.txt)
   - ● Modified (test1.txt)
   - ● Renamed (test1.txt → test_renamed.txt)
   - ● Created (test2.txt)
   - ● Deleted (test2.txt)

3. Go to Logs page - should see all events in "Activity Logs"

### Step 5: Stop Monitoring
1. Click "Stop Monitoring" button
2. Status changes to "Stopped"
3. Events no longer logged

---

## Event Color Coding

The dashboard uses color-coded indicators for easy identification:

- **Green (●)** - File Created
- **Red (●)** - File Deleted
- **Orange (●)** - File Modified
- **Blue (●)** - File Renamed/Moved

---

## Technical Details

### Background Monitoring
- Runs in separate thread (non-blocking)
- Uses watchdog Observer pattern
- Recursive monitoring (includes subfolders)
- Thread-safe with locks for multi-user support

### Modified Event Debouncing
To prevent log spam, modified events have a 2-second cooldown per file:
```python
self.modified_debounce = 2.0  # seconds
```

If the same file is modified twice within 2 seconds, only the first event is logged.

### Database Storage
All events are stored in SQLite with:
```sql
INSERT INTO logs (
    username,      -- Logged-in user
    action,        -- file_created/deleted/modified/renamed
    filename,      -- Full file path
    status,        -- success/error
    message,       -- Descriptive message
    timestamp,     -- ISO 8601 format
    session_id     -- User session ID
)
```

### Log File
Events are also written to `log.txt`:
```
2026-02-18T10:45:23 | abc123xyz | admin | file_created | test.txt | success | File created: C:\...\test.txt
```

---

## Multi-User Isolation

Each user's monitoring is isolated:
- User A monitors Folder X → sees only their events
- User B monitors Folder Y → sees only their events
- Sessions tracked by `username_sessionid` key

---

## Troubleshooting

### Events Not Appearing?

1. **Check monitoring status:** Dashboard should show "Running"
2. **Verify folder path:** Must be valid, existing directory
3. **Check permissions:** User must have read access to folder
4. **Refresh page:** Events are fetched on page load (not real-time push)
5. **Check logs table:** View all logs in Logs page

### Only Seeing Delete Events?

This was the original issue - now fixed with improved event handlers:
- All 4 event types now properly detected
- Modified events debounced to prevent spam
- Directory events filtered out (only files)

### Too Many Modified Events?

Adjust the debounce timer in `file_monitor.py`:
```python
self.modified_debounce = 5.0  # Increase to 5 seconds
```

---

## Windows-Specific Notes

On Windows, watchdog uses:
- ReadDirectoryChangesW API
- Asynchronous I/O
- Native file system notifications

Some caveats:
- Very rapid changes might coalesce
- Network drives may not support monitoring
- Large folders (10k+ files) may be slower to initialize

---

## Production Recommendations

For enterprise deployment:

1. **Database indexing:**
   ```sql
   CREATE INDEX idx_logs_username_action ON logs(username, action);
   CREATE INDEX idx_logs_timestamp ON logs(timestamp);
   ```

2. **Log rotation:**
   - Archive old logs (30+ days)
   - Prevent unbounded database growth

3. **Event filtering:**
   - Add whitelist/blacklist for file extensions
   - Ignore temp files (.tmp, .swp, etc.)

4. **Resource limits:**
   - Limit monitored folders per user
   - Set max observers per system

5. **Real-time updates:**
   - Implement WebSocket for live dashboard updates
   - Use Flask-SocketIO for push notifications

---

## Summary

The file monitoring system now fully detects:
✅ File created
✅ File deleted
✅ File modified (debounced)
✅ File renamed/moved

All events are:
✅ Logged to SQLite database
✅ Written to log.txt file
✅ Displayed on dashboard with color coding
✅ Scoped per user (multi-user isolation)
✅ Running continuously in background thread

**Result:** Professional enterprise-grade real-time file monitoring system with comprehensive event detection and audit logging.
