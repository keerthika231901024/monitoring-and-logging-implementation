import os
import shutil
import hashlib
from datetime import datetime

from exceptions import FileOperationError, ValidationError


class FileOrganizer:
    def __init__(self, logger):
        self.logger = logger
        self.extension_map = {
            "Images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
            "Documents": {".pdf", ".doc", ".docx", ".txt", ".xlsx"},
            "Videos": {".mp4", ".mov", ".avi", ".mkv"},
            "Code": {".py", ".js", ".ts", ".html", ".css", ".json"},
        }
        
        # Windows system folder mapping
        self.system_folder_map = {
            "Pictures": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
            "Documents": {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".ppt", ".pptx"},
            "Music": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
            "Videos": {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"},
            "Downloads": set()  # Default for everything else
        }
    
    def _get_windows_username(self):
        """Get the current Windows username."""
        try:
            return os.getlogin()
        except:
            return os.environ.get('USERNAME', 'User')
    
    def _get_system_folder_path(self, folder_name):
        """Get the full path to a Windows system folder."""
        windows_username = self._get_windows_username()
        base_path = f"C:/Users/{windows_username}/{folder_name}"
        os.makedirs(base_path, exist_ok=True)
        return base_path
    
    def _get_system_category(self, extension):
        """Determine which Windows system folder a file should go to based on extension."""
        for folder_name, extensions in self.system_folder_map.items():
            if folder_name == "Downloads":
                continue  # Skip Downloads, it's the default
            if extension in extensions:
                return folder_name
        return "Downloads"
    
    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of a file for duplicate detection.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            SHA256 hash string or None if file cannot be read
        """
        try:
            sha256_hash = hashlib.sha256()
            # Read file in chunks to handle large files efficiently
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            return None
    
    def find_duplicates(self, file_path, target_folder):
        """Search for duplicate files in target folder using hash comparison.
        
        Args:
            file_path: Path to the uploaded file
            target_folder: Destination folder to search in
            
        Returns:
            List of duplicate file paths found, or empty list if none
        """
        try:
            if not os.path.exists(file_path):
                return []
            
            # Calculate hash of the uploaded file
            source_hash = self.calculate_file_hash(file_path)
            if not source_hash:
                return []
            
            duplicates = []
            
            # Search through all files in target folder
            if os.path.exists(target_folder):
                for filename in os.listdir(target_folder):
                    file_in_folder = os.path.join(target_folder, filename)
                    
                    # Only compare regular files
                    if not os.path.isfile(file_in_folder):
                        continue
                    
                    # Skip the source file itself (if already in destination)
                    if os.path.abspath(file_in_folder) == os.path.abspath(file_path):
                        continue
                    
                    # Compare hashes
                    folder_file_hash = self.calculate_file_hash(file_in_folder)
                    if folder_file_hash == source_hash:
                        duplicates.append(file_in_folder)
            
            return duplicates
            
        except Exception as e:
            return []
    
    def delete_duplicates(self, duplicate_paths, username, session_id):
        """Safely delete duplicate files.
        
        Args:
            duplicate_paths: List of file paths to delete
            username: Username for logging
            session_id: Session ID for tracking
            
        Returns:
            Dictionary with deletion results
        """
        deleted_count = 0
        failed_count = 0
        
        for dup_path in duplicate_paths:
            try:
                if os.path.exists(dup_path) and os.path.isfile(dup_path):
                    # Get file info before deletion
                    file_name = os.path.basename(dup_path)
                    file_size = os.path.getsize(dup_path)
                    
                    # Delete the duplicate
                    os.remove(dup_path)
                    
                    # Log deletion
                    self.logger.log(
                        username,
                        "duplicate_deleted",
                        file_name,
                        "success",
                        f"Duplicate removed from {dup_path} (Size: {file_size} bytes)",
                        session_id,
                    )
                    deleted_count += 1
                    
            except Exception as e:
                failed_count += 1
                try:
                    file_name = os.path.basename(dup_path)
                    self.logger.log(
                        username,
                        "duplicate_delete_error",
                        file_name,
                        "error",
                        f"Failed to delete duplicate at {dup_path}: {str(e)}",
                        session_id,
                    )
                except:
                    pass
        
        return {
            "deleted": deleted_count,
            "failed": failed_count
        }
    
    def _cleanup_temp_file(self, temp_file_path, filename, username, session_id):
        """Safely delete temporary upload file with comprehensive logging."""
        cleanup_result = {
            "success": True,
            "deleted": False,
            "message": ""
        }
        
        try:
            if not os.path.exists(temp_file_path):
                cleanup_result["message"] = "Temp file already removed"
                cleanup_result["deleted"] = True
                return cleanup_result
            
            file_size = 0
            try:
                file_size = os.path.getsize(temp_file_path)
            except:
                pass
            
            try:
                os.remove(temp_file_path)
            except Exception as exc:
                cleanup_result["success"] = False
                cleanup_result["message"] = f"Error deleting temp file: {str(exc)}"
                self.logger.log(
                    username,
                    "temp_file_delete_error",
                    filename,
                    "error",
                    f"Failed to delete temp file: {str(exc)}",
                    session_id,
                )
                return cleanup_result
            
            if os.path.exists(temp_file_path):
                cleanup_result["success"] = False
                cleanup_result["message"] = "Temp file deletion verification failed"
                return cleanup_result
            
            cleanup_result["deleted"] = True
            cleanup_result["message"] = f"Temp file deleted successfully ({file_size} bytes)"
            
            self.logger.log(
                username,
                "temp_file_deleted",
                filename,
                "success",
                f"Original temp file removed from upload folder (Size: {file_size} bytes)",
                session_id,
            )
            
            return cleanup_result
            
        except Exception as exc:
            cleanup_result["success"] = False
            cleanup_result["message"] = f"Unexpected error during temp cleanup: {str(exc)}"
            return cleanup_result

    def find_duplicates_across_system(self, file_path, filename, exclude_folder=None):
        """Search for duplicate files across all common Windows system folders.
        
        This performs a system-wide scan to find copies of a file in:
        - Downloads folder
        - Desktop folder  
        - Documents folder
        - Pictures folder
        - Videos folder
        - Music folder
        - uploads/temp folder (temporary uploads)
        
        Uses SHA256 hash comparison to detect duplicates regardless of filename.
        
        Args:
            file_path: Path to the file to search for (provides hash reference)
            filename: Name of file being organized
            exclude_folder: Folder path to exclude from search (e.g., destination folder)
            
        Returns:
            Dictionary with:
            - duplicates: List of duplicate file paths found
            - locations: Dict mapping folder names to found duplicates
            - total_found: Count of total duplicates found
        """
        result = {
            "duplicates": [],
            "locations": {},
            "total_found": 0
        }
        
        try:
            # Calculate hash of the source file
            source_hash = self.calculate_file_hash(file_path)
            if not source_hash:
                return result
            
            # Get list of all system folders to scan
            windows_username = self._get_windows_username()
            system_folders = {
                "Downloads": f"C:/Users/{windows_username}/Downloads",
                "Desktop": f"C:/Users/{windows_username}/Desktop",
                "Documents": f"C:/Users/{windows_username}/Documents",
                "Pictures": f"C:/Users/{windows_username}/Pictures",
                "Videos": f"C:/Users/{windows_username}/Videos",
                "Music": f"C:/Users/{windows_username}/Music",
                "Uploads": f"C:/Users/{windows_username}/Desktop/AI/uploads"
            }
            
            # Scan each system folder for duplicates
            for folder_label, folder_path in system_folders.items():
                if not os.path.exists(folder_path):
                    continue
                
                # Skip the exclude folder if provided
                if exclude_folder and os.path.abspath(folder_path) == os.path.abspath(exclude_folder):
                    continue
                
                folder_duplicates = []
                
                try:
                    for item_name in os.listdir(folder_path):
                        item_path = os.path.join(folder_path, item_name)
                        
                        # Only process regular files
                        if not os.path.isfile(item_path):
                            continue
                        
                        # Skip the source file itself
                        if os.path.abspath(item_path) == os.path.abspath(file_path):
                            continue
                        
                        # Calculate hash and compare
                        try:
                            item_hash = self.calculate_file_hash(item_path)
                            if item_hash == source_hash:
                                folder_duplicates.append(item_path)
                                result["duplicates"].append(item_path)
                        except:
                            # Skip files that can't be read
                            continue
                    
                    if folder_duplicates:
                        result["locations"][folder_label] = folder_duplicates
                        result["total_found"] += len(folder_duplicates)
                        
                except Exception as folder_exc:
                    # Continue scanning other folders if one fails
                    continue
            
            return result
            
        except Exception as exc:
            # Return empty result on critical error
            return result

    def get_file_destination_info(self, filename):
        """Get info about where a file would be organized."""
        _, ext = os.path.splitext(filename)
        category = self._get_system_category(ext.lower())
        return {
            "category": category,
            "destination_folder": self._get_system_folder_path(category),
            "extension": ext.lower()
        }

    def _resolve_destination(self, base_folder, filename):
        name, ext = os.path.splitext(filename)
        destination = os.path.join(base_folder, filename)
        counter = 1
        while os.path.exists(destination):
            destination = os.path.join(base_folder, f"{name}_{counter}{ext}")
            counter += 1
        return destination

    def _get_category(self, extension):
        for folder, extensions in self.extension_map.items():
            if extension in extensions:
                return folder
        return "Other"

    def organize_to_system_folders(self, file_path, filename, session_id, username):
        """Organize a single file to Windows system folders with automatic duplicate handling.
        
        This method:
        1. Detects file type and destination folder
        2. Searches for and removes duplicate files
        3. Moves file using true cut+paste behavior
        4. Logs all operations
        
        Args:
            file_path: Current path of the file
            filename: Name of the file
            session_id: Session ID for tracking
            username: Username performing the action
            
        Returns:
            Dictionary with success status, destination, and details
        """
        try:
            # Verify source file exists
            if not os.path.exists(file_path):
                error_msg = f"Source file not found: {file_path}"
                self.logger.log(username, "organize_error", filename, "error", error_msg, session_id)
                return {"success": False, "error": error_msg, "message": error_msg}
            
            # Get file extension and determine destination folder
            _, ext = os.path.splitext(filename)
            category = self._get_system_category(ext.lower())
            target_folder = self._get_system_folder_path(category)
            
            # Log file categorization
            self.logger.log(
                username,
                "file_categorized",
                filename,
                "success",
                f"File categorized as {category}",
                session_id,
            )
            
            # Calculate hash of incoming file for duplicate detection
            incoming_hash = self.calculate_file_hash(file_path)
            
            # Search for duplicate files in destination folder
            duplicates_found = self.find_duplicates(file_path, target_folder)
            
            if duplicates_found:
                # Log duplicate discovery
                self.logger.log(
                    username,
                    "duplicate_found",
                    filename,
                    "success",
                    f"Found {len(duplicates_found)} duplicate(s) in {target_folder}",
                    session_id,
                )
                
                # Delete all duplicates
                deletion_result = self.delete_duplicates(duplicates_found, username, session_id)
                
                # Log cleanup summary
                if deletion_result["deleted"] > 0:
                    self.logger.log(
                        username,
                        "cleanup_completed",
                        filename,
                        "success",
                        f"Removed {deletion_result['deleted']} duplicate(s)",
                        session_id,
                    )
            
            # Resolve destination path (handle filename conflicts)
            destination = self._resolve_destination(target_folder, filename)
            
            # Perform the move operation (true cut+paste behavior)
            try:
                shutil.move(file_path, destination)
            except Exception as move_exc:
                error_msg = f"Failed to move file: {str(move_exc)}"
                raise FileOperationError(error_msg)
            
            # Verify file was moved successfully
            if not os.path.exists(destination):
                error_msg = f"File move verification failed: {destination}"
                raise FileOperationError(error_msg)
            
            # Log successful move
            self.logger.log(
                username,
                "file_moved_successfully",
                filename,
                "success",
                f"File moved to {destination}",
                session_id,
            )
            
            # After shutil.move(), verify original is gone and clean up if needed
            if os.path.exists(file_path):
                cleanup_result = self._cleanup_temp_file(file_path, filename, username, session_id)
                if not cleanup_result["deleted"]:
                    self.logger.log(
                        username,
                        "original_file_cleanup_failed",
                        filename,
                        "warning",
                        f"Original temp file could not be deleted from {file_path}",
                        session_id,
                    )
            
            # SYSTEM-WIDE DUPLICATE SCAN: Search all system folders for copies of this file
            # This ensures only ONE copy of the file exists in the entire system
            system_wide_duplicates = self.find_duplicates_across_system(destination, filename, exclude_folder=target_folder)
            system_wide_deleted_count = 0
            
            if system_wide_duplicates["total_found"] > 0:
                # Log discovery of system-wide duplicates
                self.logger.log(
                    username,
                    "system_wide_duplicates_found",
                    filename,
                    "success",
                    f"Found {system_wide_duplicates['total_found']} duplicate(s) across system folders: {', '.join(system_wide_duplicates['locations'].keys())}",
                    session_id,
                )
                
                # Delete all system-wide duplicates
                system_deletion_result = self.delete_duplicates(system_wide_duplicates["duplicates"], username, session_id)
                system_wide_deleted_count = system_deletion_result["deleted"]
                
                if system_wide_deleted_count > 0:
                    self.logger.log(
                        username,
                        "system_wide_cleanup_completed",
                        filename,
                        "success",
                        f"Removed {system_wide_deleted_count} duplicate(s) from system folders: {', '.join(system_wide_duplicates['locations'].keys())}",
                        session_id,
                    )
            
            # Total duplicates removed (destination folder + system-wide)
            total_duplicates_removed = len(duplicates_found) + system_wide_deleted_count
            
            # Build user-friendly message with cleanup details
            if system_wide_deleted_count > 0:
                location_labels = list(system_wide_duplicates['locations'].keys())
                friendly_message = f"{filename} moved to {category} folder • {system_wide_deleted_count} old copies removed from {' and '.join(location_labels)}"
            else:
                friendly_message = f"{filename} moved to {category} folder"
            
            # Log successful organization with comprehensive details
            self.logger.log(
                username,
                "uploaded_and_organized",
                filename,
                "success",
                friendly_message,
                session_id,
            )
            
            # Log comprehensive organization summary
            self.logger.log(
                username,
                "organization_summary",
                filename,
                "success",
                f"{filename} → {destination} | Destination duplicates: {len(duplicates_found)} removed | System-wide duplicates: {system_wide_deleted_count} removed | Total cleaned: {total_duplicates_removed}",
                session_id,
            )
            
            return {
                "success": True,
                "category": category,
                "destination": destination,
                "message": friendly_message,
                "duplicates_removed": len(duplicates_found),
                "system_wide_duplicates_removed": system_wide_deleted_count,
                "total_duplicates_removed": total_duplicates_removed,
                "file_hash": incoming_hash
            }
            
        except Exception as exc:
            error_message = f"Failed to organize {filename}: {str(exc)}"
            self.logger.log(
                username,
                "organize_error",
                filename,
                "error",
                error_message,
                session_id,
            )
            return {
                "success": False,
                "error": str(exc),
                "message": error_message
            }
    
    def confirm_organization(self, temp_file_path, filename, session_id, username):
        """User confirmed organization. Move file from temp to system folder."""
        return self.organize_to_system_folders(temp_file_path, filename, session_id, username)
    
    def reject_organization(self, filename, session_id, username):
        """User rejected organization. Keep file in uploads folder."""
        message = f"{filename} kept in uploads folder (not organized)"
        self.logger.log(
            username,
            "upload_kept",
            filename,
            "success",
            message,
            session_id,
        )
        return {
            "success": True,
            "message": message,
            "action": "kept"
        }
    
    def organize_folder(self, folder_path, session_id, username):
        if not folder_path:
            raise ValidationError("Folder path is required.")
        if not os.path.exists(folder_path):
            raise ValidationError("Folder path does not exist.")
        if not os.path.isdir(folder_path):
            raise ValidationError("Provided path is not a folder.")

        total_files = 0
        total_errors = 0

        for entry in os.listdir(folder_path):
            source_path = os.path.join(folder_path, entry)
            if os.path.isdir(source_path):
                continue

            total_files += 1
            _, ext = os.path.splitext(entry)
            category = self._get_category(ext.lower())
            target_folder = os.path.join(folder_path, category)
            os.makedirs(target_folder, exist_ok=True)

            try:
                destination = self._resolve_destination(target_folder, entry)
                shutil.move(source_path, destination)
                self.logger.log(
                    username,
                    "file_moved",
                    entry,
                    "success",
                    f"Moved to {category}",
                    session_id,
                )
            except Exception as exc:
                total_errors += 1
                self.logger.log(
                    username,
                    "file_error",
                    entry,
                    "error",
                    f"Failed to move: {exc}",
                    session_id,
                )

        if total_files == 0:
            raise FileOperationError("No files found to organize.")

        return {"total_files": total_files, "total_errors": total_errors}
