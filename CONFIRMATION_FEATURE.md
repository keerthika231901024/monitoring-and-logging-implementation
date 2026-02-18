# File Upload Confirmation Feature

## Overview
The Flask File Organizer system has been upgraded with a **user confirmation workflow** before automatic file organization. When a user uploads a file, they now get to decide whether to organize it to the system folder or keep it in the uploads folder.

## How It Works

### 1. File Upload Process

**Before Confirmation Feature:**
```
File Uploaded → Automatically Organized to System Folder
```

**After Confirmation Feature:**
```
File Uploaded → Saved to Temp Folder → Show Confirmation → User Action
                                          ↓
                            Yes, Organize              No, Keep
                                  ↓                         ↓
                    Move to System Folder         Keep in Uploads Folder
                    (Pictures/Documents/etc)
```

### 2. Upload Flow

#### Step 1: Upload File
- User selects file from dashboard "Quick Upload" section
- File is saved to `uploads/temp/` folder temporarily
- Dashboard shows: `"File uploaded successfully! Do you want to organize it to [Category] folder?"`

#### Step 2: View Pending Upload
- File appears in **"Pending Uploads"** section on dashboard
- Shows:
  - Upload Time
  - Filename
  - Suggested Category (Pictures, Documents, Music, Videos, Downloads)
  - Two Action Buttons: **Organize** | **Keep**

#### Step 3a: User Clicks "Organize"
```
1. File moved from uploads/temp/ to system folder
   - Images → C:/Users/<username>/Pictures/
   - PDFs/Docs → C:/Users/<username>/Documents/
   - Music → C:/Users/<username>/Music/
   - Videos → C:/Users/<username>/Videos/
   - Other → C:/Users/<username>/Downloads/

2. Temp file deleted automatically

3. Logged in database with action = "uploaded_and_organized"
   Message: "butterfly.jpg moved to Pictures folder after confirmation"

4. File moves to "Organized Files" section on dashboard (green text)
```

#### Step 3b: User Clicks "Keep"
```
1. File moved from uploads/temp/ to uploads/ folder

2. Logged in database with action = "upload_kept"
   Message: "butterfly.jpg kept in uploads folder (not organized)"

3. File is available in uploads folder for later organization

4. Removes from "Pending Uploads" section
```

## Dashboard Sections

### 1. Quick Upload (Top Left)
```
Simple file upload form with:
- File input field
- Upload button
```

### 2. Pending Uploads (Top Right) - NEW!
```
Table showing files waiting for confirmation:

| Time | File | Action | Status |
|------|------|--------|--------|
| 2026-02-18 10:30 | photo.jpg | [Organize] [Keep] | success |
| 2026-02-18 10:31 | report.pdf | [Organize] [Keep] | success |
```

**Colors:**
- **Organize button**: Dark Green (#27ae60) - Confirms organization
- **Keep button**: Gray (#95a5a6) - Keeps in uploads

### 3. Organized Files (Below)
```
Table showing completed organization:

| Time | File | Organized To | Status |
|------|------|-------------|--------|
| 2026-02-18 10:32 | photo.jpg | photo.jpg moved to Pictures folder after confirmation | success |
| 2026-02-18 10:33 | report.pdf | report.pdf moved to Documents folder after confirmation | success |
```

- Message text shown in **green** (#2ecc71)
- Shows user-friendly destination ("Pictures folder", "Documents folder")

## File Organization Logic

### Extension Mapping

```python
Pictures (Images)          → .jpg, .png, .gif, .bmp, .webp
Documents (PDFs/Text)      → .pdf, .doc, .docx, .txt, .xlsx, .xls, .ppt, .pptx
Music                      → .mp3, .wav, .flac, .aac, .ogg, .m4a
Videos                     → .mp4, .mov, .avi, .mkv, .flv, .wmv
Downloads (Other Files)    → Everything else
```

### Duplicate Handling
If file exists in destination folder:
- `photo.jpg` → `photo_1.jpg` → `photo_2.jpg` (etc.)

## Database Logging

### New Actions Logged

1. **upload_pending**
   - Action after file uploaded to temp folder
   - Message: "File uploaded. Waiting for user confirmation to organize to [Category]"
   - Status: success

2. **uploaded_and_organized**
   - Action after user confirms organization
   - Message: "[filename] moved to [Category] folder after confirmation"
   - Status: success

3. **upload_kept**
   - Action after user chooses to keep file in uploads
   - Message: "[filename] kept in uploads folder (not organized)"
   - Status: success

4. **organize_error** / **reject_organize_error**
   - Actions if something fails during organization or rejection
   - Message: Error description
   - Status: error

### Database Schema
```
logs table columns:
- id (primary key)
- username (logged-in user)
- action (upload_pending, uploaded_and_organized, upload_kept, organize_error, etc.)
- filename (the file)
- status (success, error)
- message (user-friendly description)
- timestamp (ISO format datetime)
- session_id (user's session)
```

## File Paths

### Temp Upload Location
```
C:/Users/idpuser/Desktop/AI/uploads/temp/
```

### Permanent Upload Location (if kept)
```
C:/Users/idpuser/Desktop/AI/uploads/
```

### Windows System Folders (if organized)
```
C:/Users/<username>/Pictures/
C:/Users/<username>/Documents/
C:/Users/<username>/Music/
C:/Users/<username>/Videos/
C:/Users/<username>/Downloads/
```

## API Routes

### Upload
```
POST /upload
Parameters: file (multipart form data)
Result: Saves to temp, shows pending upload
```

### Confirm Organization
```
POST /confirm_organize/<filename>
Result: Moves file to system folder, logs action, deletes temp file
```

### Reject Organization
```
POST /reject_organize/<filename>
Result: Moves file from temp to uploads folder, logs action
```

## Code Changes

### Modified Files

1. **app.py**
   - Added `TEMP_UPLOAD_FOLDER` constant
   - Modified `/upload` route to save to temp and show confirmation
   - Added `/confirm_organize/<filename>` route
   - Added `/reject_organize/<filename>` route
   - Updated `/dashboard` route to fetch pending_uploads and organized_logs
   - Added `import shutil` for file operations

2. **organizer.py**
   - Added `get_file_destination_info()` method
   - Added `confirm_organization()` method
   - Added `reject_organization()` method
   - Updated message text to show "after confirmation"

3. **database_manager.py**
   - Added `get_pending_uploads()` method to fetch pending files

4. **templates/dashboard.html**
   - Added "Pending Uploads" section with Organize/Keep buttons
   - Renamed "Upload History" to "Organized Files"
   - Updated upload_logs reference to organized_logs

5. **static/styles.css**
   - Added `.confirm-btn` styling (green)
   - Added `.reject-btn` styling (gray)

## Testing the Feature

### Test Case 1: Upload and Confirm Organization
1. Login to dashboard
2. Upload an image file (e.g., photo.jpg)
3. See "Pending Uploads" section with photo.jpg
4. Click **Organize** button
5. Check Windows File Explorer: File should be in Pictures folder
6. Dashboard shows: "photo.jpg moved to Pictures folder after confirmation"

### Test Case 2: Upload and Keep in Uploads
1. Upload a document file (e.g., report.pdf)
2. See "Pending Uploads" section with report.pdf
3. Click **Keep** button
4. File moves to `uploads/` folder
5. Dashboard shows: "report.pdf kept in uploads folder (not organized)"

### Test Case 3: Duplicate Filename
1. Upload photo.jpg (organize it)
2. Upload another photo.jpg file (organize it)
3. First goes to C:/Users/<username>/Pictures/photo.jpg
4. Second goes to C:/Users/<username>/Pictures/photo_1.jpg

## Benefits

✅ **User Control**: Users decide if they want automatic organization
✅ **Safe**: No destructive operations without confirmation
✅ **Audit Trail**: Every action is logged with timestamps
✅ **Professional UX**: Clean, intuitive confirmation interface
✅ **Undo-Friendly**: Users can keep files instead of organizing
✅ **Real-Time Feedback**: Immediate dashboard updates
✅ **Error Handling**: Graceful failure messages and logging

## System Folders Auto-Detection

The system automatically:
1. Detects Windows username using `os.getlogin()` or `os.environ.get('USERNAME')`
2. Creates system folders if they don't exist
3. Maps file extensions to correct folders
4. Handles filename collisions with counter

No manual path configuration needed!
