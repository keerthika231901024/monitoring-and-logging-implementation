# Upload Confirmation Workflow - Quick Reference

## File Organization Decision Tree

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER UPLOADS FILE                            │
│                                                                   │
│  1. User selects file from dashboard                            │
│  2. File saved to: uploads/temp/[filename]                      │
│  3. Gets file type: .jpg, .pdf, .mp3, etc.                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────▼────────────┐
                │  DATABASE LOGS ACTION   │
                │  action="upload_pending"│
                │  Status: success        │
                └────────────┬────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │    SHOWN IN "PENDING UPLOADS"       │
          │                                     │
          │  Time: 10:30 AM                    │
          │  File: photo.jpg                   │
          │  Buttons: [Organize] [Keep]        │
          └──────────────┬─────────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
    ┌─────────▼────────┐   ┌────────▼────────┐
    │ CLICK ORGANIZE   │   │  CLICK KEEP     │
    └─────────┬────────┘   └────────┬────────┘
              │                     │
    ┌─────────▼────────┐   ┌────────▼───────────┐
    │ Detect Category  │   │  Move temp file to │
    │ by extension:    │   │  permanent uploads │
    │ .jpg → Pictures  │   │  folder            │
    │ .pdf → Documents │   └────────┬───────────┘
    │ .mp3 → Music     │            │
    │ .mp4 → Videos    │   ┌────────▼──────────┐
    │ Other→ Downloads │   │DATABASE LOGS      │
    └─────────┬────────┘   │action="upload_kept"
              │            │Status: success
    ┌─────────▼────────┐   └────────┬──────────┘
    │ Create system    │            │
    │ folder if needed │   ┌────────▼──────────────┐
    │ C:/Users/../Pic/ │   │ SHOWN IN DASHBOARD:   │
    │ C:/Users/../Docs │   │ "[filename] kept in   │
    │ etc.             │   │  uploads folder"      │
    └─────────┬────────┘   └───────────────────────┘
              │
    ┌─────────▼────────────────┐
    │ Move file from temp to   │
    │ system folder:           │
    │ uploads/temp/photo.jpg   │
    │         ↓                │
    │ C:/Users/../Pictures/    │
    └─────────┬────────────────┘
              │
    ┌─────────▼─────────┐
    │ Delete temp file  │
    │ from: uploads/temp│
    └─────────┬─────────┘
              │
    ┌─────────▼──────────────┐
    │DATABASE LOGS           │
    │action="uploaded_and_   │
    │ organized"             │
    │Status: success         │
    │Message: "photo.jpg     │
    │moved to Pictures       │
    │folder after confirm"   │
    └─────────┬──────────────┘
              │
    ┌─────────▼──────────────────┐
    │ FILE APPEARS IN:           │
    │ "ORGANIZED FILES" SECTION  │
    │ Green text shows:          │
    │ "[filename] moved to       │
    │  [Folder] folder after     │
    │  confirmation"             │
    └────────────────────────────┘
```

## Action Comparison

| Action | Source | Destination | Database Action | Log Message |
|--------|--------|-------------|-----------------|-------------|
| **Organize** | uploads/temp/ | System folder (Pictures/Documents/etc) | uploaded_and_organized | "[filename] moved to [Folder] folder after confirmation" |
| **Keep** | uploads/temp/ | uploads/ | upload_kept | "[filename] kept in uploads folder (not organized)" |

## Dashboard Views Timeline

### State 1: After Upload
```
┌──────────────────────────────────────────────┐
│       PENDING UPLOADS (shows new file)       │
├──────────────────────────────────────────────┤
│ Time | File      | Action               |    │
│─────┼───────────┼──────────────────────────  │
│10:30│photo.jpg │ [Organize] [Keep]     │    │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│       ORGANIZED FILES (empty)                │
├──────────────────────────────────────────────┤
│ No organized files yet                       │
└──────────────────────────────────────────────┘
```

### State 2: After Clicking "Organize"
```
┌──────────────────────────────────────────────┐
│       PENDING UPLOADS (removed)              │
├──────────────────────────────────────────────┤
│ No pending uploads                           │
└──────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│       ORGANIZED FILES (shows organized)           │
├────────────────────────────────────────────────────┤
│ Time |File     | Organized To              | St  │
│─────┼─────────┼──────────────────────────────────  │
│10:32│photo.jpg│ photo.jpg moved to Pictures│ ✓   │
└────────────────────────────────────────────────────┘
```

## Folder Structure

### Before Upload
```
AI/
├── uploads/
│   └── (existing files)
├── uploads/temp/
│   └── (empty)
└── ... other files
```

### During Upload (Before Confirmation)
```
AI/
├── uploads/
│   ├── (existing files)
│   └── temp/
│       └── photo.jpg  ← Just uploaded, waiting for confirmation
└── ... other files
```

### After Confirmation - "Organize" Button
```
AI/
├── uploads/
│   ├── (existing files)
│   └── temp/
│       └── (empty - file moved)

System Folders:
C:/Users/idpuser/Pictures/
└── photo.jpg  ← File moved here after confirmation
```

### After Confirmation - "Keep" Button
```
AI/
├── uploads/
│   ├── (existing files)
│   └── photo.jpg  ← File moved here, kept in uploads
└── ... other files
```

## How to Trigger Each Flow

### Organize Flow
```python
# Routes
POST /upload
    └─> Save to uploads/temp/
    └─> Log: upload_pending
    └─> Dashboard shows pending file

POST /confirm_organize/<filename>
    └─> Move: uploads/temp/ → System folder
    └─> Delete: uploads/temp/[file]
    └─> Log: uploaded_and_organized
    └─> Dashboard moves to "Organized Files"
```

### Keep Flow
```python
POST /upload
    └─> Save to uploads/temp/
    └─> Log: upload_pending
    └─> Dashboard shows pending file

POST /reject_organize/<filename>
    └─> Move: uploads/temp/ → uploads/
    └─> Log: upload_kept
    └─> Dashboard removes from pending
```

## Error Handling

### If File Doesn't Exist
```
Message: "File not found: [filename]"
Flash Type: error
No changes made
```

### If Move Fails
```
Message: "Organization failed: [error details]"
Flash Type: error
Logged: organize_error action with full error message
```

### If Temp Folder Can't Be Created
```
Already handled by os.makedirs(exist_ok=True)
Creates folder automatically
```

## Session-Based Uniqueness

- Each user has separate pending_uploads list
- Session ID tracked with each action
- Multiple users can have pending uploads simultaneously
- No interference between users

Example:
```
User A uploaded: photo.jpg (pending)
User B uploaded: document.pdf (pending)
↓
User A sees only: photo.jpg in pending uploads
User B sees only: document.pdf in pending uploads
```
