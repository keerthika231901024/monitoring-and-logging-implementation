import os
from exceptions import FileOperationError, ValidationError


class FileManager:
    """Manages file operations like deletion with logging."""

    def __init__(self, logger, db_manager):
        self.logger = logger
        self.db = db_manager

    def verify_file_ownership(self, username, filename):
        """Verify that the file was uploaded by the given user."""
        logs = self.db.get_logs_by_action(username, "upload", limit=1000)
        for log in logs:
            if log["filename"] == filename and log["status"] == "success":
                return True
        return False

    def delete_file(self, username, filename, file_path, session_id):
        """
        Delete a file from storage and log the action.
        
        Args:
            username: The user requesting deletion
            filename: Name of the file to delete
            file_path: Full path to the file
            session_id: Current session ID
            
        Returns:
            dict with success status and message
        """
        if not filename:
            raise ValidationError("Filename is required.")

        # Verify ownership
        if not self.verify_file_ownership(username, filename):
            self.logger.log(
                username,
                "delete",
                filename,
                "error",
                "Permission denied: file not owned by user",
                session_id,
            )
            raise FileOperationError("You can only delete files you uploaded.")

        # Check if file exists
        if not os.path.exists(file_path):
            self.logger.log(
                username,
                "delete",
                filename,
                "error",
                "File not found",
                session_id,
            )
            raise FileOperationError("File not found.")

        try:
            # Delete the physical file
            os.remove(file_path)
            
            # Log successful deletion
            self.logger.log(
                username,
                "delete",
                filename,
                "success",
                "File deleted successfully",
                session_id,
            )
            
            return {
                "success": True,
                "message": f"File '{filename}' deleted successfully."
            }
            
        except PermissionError:
            self.logger.log(
                username,
                "delete",
                filename,
                "error",
                "Permission denied",
                session_id,
            )
            raise FileOperationError("Permission denied.")
        except Exception as exc:
            self.logger.log(
                username,
                "delete",
                filename,
                "error",
                f"Deletion failed: {exc}",
                session_id,
            )
            raise FileOperationError(f"Failed to delete file: {exc}")

    def log_file_access(self, username, filename, action, session_id):
        """
        Log file access (view or download).
        
        Args:
            username: The user accessing the file
            filename: Name of the file accessed
            action: "view" or "download"
            session_id: Current session ID
        """
        if not self.verify_file_ownership(username, filename):
            self.logger.log(
                username,
                action,
                filename,
                "error",
                "Permission denied: file not owned by user",
                session_id,
            )
            raise FileOperationError("You can only access files you uploaded.")
        
        self.logger.log(
            username,
            action,
            filename,
            "success",
            f"File {action}ed: {filename}",
            session_id,
        )
