# Automatic File Organizer and Real-Time Monitoring System

## Overview
This is a professional Flask application with authentication, real-time file system monitoring, file organization, and business-grade logging. Users authenticate, then access a dashboard with live file change detection, stats, session details, and activity logs stored in SQLite.

## Features

### Core Features
- **Authentication System**: Login, registration, session management with secure password hashing
- **Multi-user Data Isolation**: Each user sees only their own logs, uploads, and monitoring data
- **SQLite Persistence**: Users, logs, and monitoring stats stored in database
- **Real-time File System Monitoring**: Detect file created, deleted, modified, renamed events
- **File Organization**: Organize files by category (Images, Documents, Videos, Code)
- **Upload Tracking**: Track all file uploads with username, timestamp, and status
- **Monitoring Dashboard**: Live system health metrics and file activity logs
- **Dual Logging**: All events logged to both SQLite database and log.txt file

### Real-Time File Monitoring
The system uses Python's **watchdog** library to continuously monitor a selected folder and detect:
- **File Created**: When a new file is added
- **File Deleted**: When a file is removed
- **File Modified**: When a file's content changes
- **File Renamed**: When a file is moved or renamed

Each event is logged with:
- Username (logged-in user)
- Action type
- Filename/path
- Timestamp (ISO format)
- Status (success/error)
- Session ID

### Start/Stop Monitoring
Users can:
1. Select a folder path from the dashboard
2. Click "Start Monitoring" to begin real-time detection
3. View live file changes in the dashboard
4. Click "Stop Monitoring" to halt detection

Monitoring runs in a background thread, so the Flask app remains responsive.

### Multi-User Support
- Each user has isolated monitoring sessions
- One user cannot see another user's logs or monitoring data
- Session-based authentication ensures secure access
- Monitoring state is tracked per user and session

## Project Structure
```
├── app.py                    # Main Flask application with routes
├── auth_manager.py           # User authentication logic
├── database_manager.py       # SQLite database operations
├── organizer.py              # File organization by type
├── logger.py                 # Logging to database and file
├── system_monitor.py         # System stats and health monitoring
├── file_monitor.py           # Real-time file system monitoring (watchdog)
├── exceptions.py             # Custom exception classes
├── templates/                # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── organize.html
│   ├── logs.html
│   └── error.html
├── static/
│   └── styles.css            # Modern dashboard styling
├── app.db                    # SQLite database (auto-created)
├── log.txt                   # Text file logs (auto-created)
└── uploads/                  # User uploaded files
```

## Run Instructions
1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**:
   ```bash
   python app.py
   ```

3. **Access the application**:
   - Open http://127.0.0.1:5000
   - Register a new account
   - Login and access the dashboard
   - Start monitoring a folder to see real-time file changes

## Database Schema
- **users**: id, username, password (hashed)
- **logs**: id, username, action, filename, status, message, timestamp, session_id
- **stats**: id, username, total_files, total_errors, last_run, session_id

## Business Use Case

### Problem Solved
Many organizations face challenges with:
1. **Missing file change audit trails**: No record of who created/modified/deleted files
2. **Lack of real-time monitoring**: Can't detect unauthorized file modifications immediately
3. **Poor visibility**: No centralized dashboard to track file operations
4. **Multi-user environments**: Need to isolate data per user for security and compliance

### Solution Provided
This system delivers:
- **Real-time monitoring**: Instant detection and logging of all file system events
- **Audit compliance**: Complete audit trail of every file change with username and timestamp
- **Accountability**: Track which user performed which action
- **Security**: Multi-user data isolation prevents information leakage
- **Business intelligence**: Dashboard shows file activity patterns and system health

### Enterprise Applications
- **IT departments**: Monitor shared drives for unauthorized changes
- **Development teams**: Track code file modifications in real-time
- **Compliance officers**: Maintain audit logs for regulatory requirements
- **System administrators**: Detect suspicious file activity immediately

## AI Usage Explanation

AI-assisted development supported this project in three critical ways:

### 1. Architecture Planning
AI helped design a modular, scalable architecture by recommending:
- **Separation of concerns**: Distinct classes for authentication, monitoring, logging, and organization
- **Thread-safe monitoring**: Using threading locks to prevent race conditions with multiple users
- **Observer pattern**: Leveraging watchdog's FileSystemEventHandler for clean event handling
- **Session-based isolation**: Using Flask sessions + username to scope all data queries

### 2. Real-Time Monitoring Strategy
AI guided the implementation of background file monitoring:
- **Watchdog integration**: Recommended watchdog library for cross-platform file system events
- **Background threading**: Suggested running observers in separate threads to keep Flask responsive
- **Event filtering**: Advised filtering directory events to reduce noise
- **Graceful shutdown**: Implemented cleanup handlers to stop all observers on app termination

### 3. Logging and Error Handling
AI designed a comprehensive logging system:
- **Dual-sink logging**: Writing to both SQLite and log.txt for redundancy
- **Structured log format**: Consistent format with timestamp, session, username, action, status
- **Custom exceptions**: Clean error hierarchy (AppError, ValidationError, AuthenticationError, FileOperationError)
- **User-friendly messages**: Separating technical errors from user-facing flash messages
- **Per-user log isolation**: Filtering all database queries by username to ensure data privacy

### 4. Professional Dashboard Design
AI recommended UX improvements:
- **Live status indicators**: Show monitoring state (Running/Stopped) prominently
- **Event counters**: Display number of detected file changes
- **Quick controls**: Start/Stop buttons directly on dashboard
- **Separate log views**: Monitoring logs, upload logs, and system logs in distinct sections

This AI-assisted approach resulted in production-ready code that demonstrates:
- Strong software engineering principles (OOP, SOLID)
- Enterprise-grade security (multi-user isolation)
- Real-time system capabilities (background monitoring)
- Professional UI/UX (modern dashboard design)

## Technologies Used
- **Backend**: Python 3.x, Flask
- **Database**: SQLite with sqlite3
- **Real-time Monitoring**: watchdog library
- **Authentication**: Werkzeug password hashing
- **Frontend**: HTML5, CSS3 (Modern dashboard design)
- **Concurrency**: Python threading
- **Logging**: Dual logging (SQLite + text file)
