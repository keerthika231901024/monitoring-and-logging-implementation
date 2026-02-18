import threading
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class FileMonitorHandler(FileSystemEventHandler):
    """Handles file system events and logs them."""

    def __init__(self, username, session_id, logger):
        super().__init__()
        self.username = username
        self.session_id = session_id
        self.logger = logger
        self.event_count = 0
        self.last_modified = {}  # Track last modified time to prevent spam
        self.modified_debounce = 2.0  # Seconds to wait before logging another modify event

    def on_created(self, event):
        """Triggered when a file or directory is created."""
        self.event_count += 1
        
        if event.is_directory:
            action = "folder_created"
            message = f"Folder created: {event.src_path}"
        else:
            action = "file_created"
            message = f"File created: {event.src_path}"
        
        self.logger.log(
            self.username,
            action,
            event.src_path,
            "success",
            message,
            self.session_id,
        )

    def on_deleted(self, event):
        """Triggered when a file or directory is deleted."""
        self.event_count += 1
        
        if event.is_directory:
            action = "folder_deleted"
            message = f"Folder deleted: {event.src_path}"
        else:
            action = "file_deleted"
            message = f"File deleted: {event.src_path}"
        
        self.logger.log(
            self.username,
            action,
            event.src_path,
            "success",
            message,
            self.session_id,
        )
        
        # Clean up modified tracking for deleted file
        if event.src_path in self.last_modified:
            del self.last_modified[event.src_path]

    def on_modified(self, event):
        """Triggered when a file or directory is modified."""
        if event.is_directory:
            return  # Skip directory modifications to reduce noise
        
        # Debounce modified events to prevent spam
        current_time = time.time()
        last_time = self.last_modified.get(event.src_path, 0)
        
        if current_time - last_time < self.modified_debounce:
            return  # Skip this event, too soon after last one
        
        self.last_modified[event.src_path] = current_time
        self.event_count += 1
        
        self.logger.log(
            self.username,
            "file_modified",
            event.src_path,
            "success",
            f"File modified: {event.src_path}",
            self.session_id,
        )

    def on_moved(self, event):
        """Triggered when a file or directory is moved or renamed."""
        self.event_count += 1
        
        if event.is_directory:
            action = "folder_renamed"
            message = f"Folder renamed/moved from {event.src_path} to {event.dest_path}"
        else:
            action = "file_renamed"
            message = f"File renamed/moved from {event.src_path} to {event.dest_path}"
        
        self.logger.log(
            self.username,
            action,
            event.dest_path,
            "success",
            message,
            self.session_id,
        )
        
        # Update modified tracking with new path
        if event.src_path in self.last_modified:
            self.last_modified[event.dest_path] = self.last_modified.pop(event.src_path)


class FileMonitor:
    """Manages file system monitoring for a specific user."""

    def __init__(self, logger):
        self.logger = logger
        self.observers = {}
        self.handlers = {}
        self.lock = threading.Lock()

    def start_monitoring(self, username, session_id, folder_path):
        """Start monitoring a folder for a specific user session."""
        with self.lock:
            monitor_key = f"{username}_{session_id}"
            
            if monitor_key in self.observers and self.observers[monitor_key].is_alive():
                self.stop_monitoring(username, session_id)

            handler = FileMonitorHandler(username, session_id, self.logger)
            observer = Observer()
            observer.schedule(handler, folder_path, recursive=True)
            observer.start()

            self.observers[monitor_key] = observer
            self.handlers[monitor_key] = handler

            self.logger.log(
                username,
                "monitoring_started",
                folder_path,
                "success",
                f"Started monitoring folder: {folder_path}",
                session_id,
            )

            return True

    def stop_monitoring(self, username, session_id):
        """Stop monitoring for a specific user session."""
        with self.lock:
            monitor_key = f"{username}_{session_id}"
            
            if monitor_key in self.observers:
                observer = self.observers[monitor_key]
                if observer.is_alive():
                    observer.stop()
                    observer.join(timeout=2)
                
                del self.observers[monitor_key]
                if monitor_key in self.handlers:
                    del self.handlers[monitor_key]

                self.logger.log(
                    username,
                    "monitoring_stopped",
                    "-",
                    "success",
                    "Stopped monitoring",
                    session_id,
                )

                return True
            return False

    def is_monitoring(self, username, session_id):
        """Check if monitoring is active for a user session."""
        monitor_key = f"{username}_{session_id}"
        return (
            monitor_key in self.observers
            and self.observers[monitor_key].is_alive()
        )

    def get_event_count(self, username, session_id):
        """Get the event count for a user session."""
        monitor_key = f"{username}_{session_id}"
        if monitor_key in self.handlers:
            return self.handlers[monitor_key].event_count
        return 0

    def stop_all(self):
        """Stop all monitoring observers."""
        with self.lock:
            for observer in self.observers.values():
                if observer.is_alive():
                    observer.stop()
            for observer in self.observers.values():
                observer.join(timeout=2)
            self.observers.clear()
            self.handlers.clear()
