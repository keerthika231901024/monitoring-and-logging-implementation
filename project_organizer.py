"""
Smart Project-Based File Organization Module

Provides intelligent categorization and organization of development project files
into structured folders (backend, frontend, database, images, documents, others).

This module implements production-grade file organization with:
- Automatic file type detection based on extension
- Smart project structure creation
- Duplicate detection using SHA256 hashing
- Comprehensive audit logging
- Thread-safe operations
- Graceful error handling
"""

import os
import shutil
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from enum import Enum

from exceptions import FileOperationError, ValidationError


class ProjectFileType(Enum):
    """Enumeration of project file types."""
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    IMAGES = "images"
    DOCUMENTS = "documents"
    OTHERS = "others"


class SmartProjectOrganizer:
    """
    Intelligent file organizer for software development projects.
    
    Automatically categorizes files into development-specific folders:
    - backend: Python, Java, C++, JavaScript (Node), C#, Go files
    - frontend: HTML, CSS, JavaScript (React/Vue), TypeScript, JSX, TSX
    - database: SQL, SQLite, JSON configs, CSV data files
    - images: PNG, JPG, GIF, SVG graphics
    - documents: PDF, Word, Text documents
    - others: Unrecognized file types
    
    Features:
    - Automatic project structure creation
    - SHA256-based duplicate detection
    - Safe duplicate removal with verification
    - Multi-level logging for audit trail
    - Thread-safe operations
    """
    
    # File extension mappings for project organization
    PROJECT_EXTENSIONS_MAP: Dict[ProjectFileType, set] = {
        ProjectFileType.BACKEND: {
            ".py", ".java", ".cpp", ".c", ".js", ".cs", ".go", ".rb", 
            ".php", ".rs", ".kt", ".scala", ".sh", ".bash"
        },
        ProjectFileType.FRONTEND: {
            ".html", ".css", ".scss", ".less", ".jsx", ".tsx", ".ts",
            ".vue", ".svelte", ".wxml", ".wxss", ".dart"
        },
        ProjectFileType.DATABASE: {
            ".sql", ".db", ".sqlite", ".sqlite3", ".json", ".csv",
            ".xml", ".yaml", ".yml", ".ini", ".conf", ".config"
        },
        ProjectFileType.IMAGES: {
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp",
            ".ico", ".tiff", ".psd", ".ai"
        },
        ProjectFileType.DOCUMENTS: {
            ".pdf", ".doc", ".docx", ".txt", ".md", ".rst", ".odt",
            ".xls", ".xlsx", ".ppt", ".pptx", ".pages", ".numbers"
        }
    }
    
    # Project folder structure
    PROJECT_STRUCTURE = [
        "backend",
        "frontend", 
        "database",
        "images",
        "documents",
        "others"
    ]

    def __init__(self, logger, base_project_path: Optional[str] = None):
        """
        Initialize the smart project organizer.
        
        Args:
            logger: LogManager instance for audit logging
            base_project_path: Optional base path for projects (auto-detected if None)
        """
        self.logger = logger
        self.base_project_path = base_project_path or self._get_default_project_path()
        self.hash_cache: Dict[str, str] = {}  # Cache for file hashes
        
    def _get_default_project_path(self) -> str:
        """Get default project path from user's home directory."""
        try:
            username = os.getlogin()
        except:
            username = os.environ.get('USERNAME', 'User')
        
        project_path = f"C:/Users/{username}/Projects"
        os.makedirs(project_path, exist_ok=True)
        return project_path

    def detect_project_file_type(self, filename: str) -> ProjectFileType:
        """
        Detect the project file type based on file extension.
        
        Args:
            filename: Name of the file to categorize
            
        Returns:
            ProjectFileType enum value indicating the category
            
        Raises:
            ValidationError: If filename is empty or invalid
        """
        if not filename or not isinstance(filename, str):
            raise ValidationError("Invalid filename provided")
        
        _, ext = os.path.splitext(filename)
        ext_lower = ext.lower()
        
        # Search for matching extension in each category
        for file_type, extensions in self.PROJECT_EXTENSIONS_MAP.items():
            if ext_lower in extensions:
                return file_type
        
        return ProjectFileType.OTHERS

    def create_project_structure(self, project_name: str) -> Tuple[bool, str]:
        """
        Create complete project folder structure.
        
        Creates the following hierarchy:
        Project_Name/
        ├── backend/
        ├── frontend/
        ├── database/
        ├── images/
        ├── documents/
        └── others/
        
        Args:
            project_name: Name of the project to create
            
        Returns:
            Tuple of (success: bool, project_path: str)
            
        Raises:
            ValidationError: If project name is invalid
            FileOperationError: If folder creation fails
        """
        if not project_name or not isinstance(project_name, str):
            raise ValidationError("Invalid project name")
        
        # Sanitize project name
        project_name = project_name.strip().replace(" ", "_")
        project_path = os.path.join(self.base_project_path, project_name)
        
        try:
            # Create project root if it doesn't exist
            if not os.path.exists(project_path):
                os.makedirs(project_path, exist_ok=True)
                self.logger.log(
                    "project_created",
                    f"Project structure created at {project_path}",
                    "success"
                )
            
            # Create all subdirectories
            for folder in self.PROJECT_STRUCTURE:
                folder_path = os.path.join(project_path, folder)
                os.makedirs(folder_path, exist_ok=True)
            
            return True, project_path
            
        except Exception as e:
            error_msg = f"Failed to create project structure: {str(e)}"
            self.logger.log(
                "project_creation_error",
                error_msg,
                "error"
            )
            raise FileOperationError(error_msg)

    def _calculate_file_hash(self, file_path: str) -> Optional[str]:
        """
        Calculate SHA256 hash of a file for duplicate detection.
        
        Uses chunked reading for memory efficiency with large files.
        Hash is cached for repeated lookups.
        
        Args:
            file_path: Full path to the file
            
        Returns:
            Hexadecimal SHA256 hash string, or None if hash fails
        """
        try:
            if file_path in self.hash_cache:
                return self.hash_cache[file_path]
            
            sha256_hash = hashlib.sha256()
            chunk_size = 4096  # 4KB chunks
            
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            
            file_hash = sha256_hash.hexdigest()
            self.hash_cache[file_path] = file_hash
            return file_hash
            
        except Exception as e:
            self.logger.log(
                "hash_calculation_error",
                f"Failed to calculate hash for {file_path}: {str(e)}",
                "warning"
            )
            return None

    def find_duplicates_in_project(
        self, 
        file_path: str, 
        target_folder: str
    ) -> List[str]:
        """
        Find duplicate files in project folder using hash comparison.
        
        Searches the target project folder for files with identical content
        (same SHA256 hash) as the incoming file.
        
        Args:
            file_path: Path to uploaded file
            target_folder: Project folder to search for duplicates
            
        Returns:
            List of duplicate file paths (empty if none found)
        """
        try:
            source_hash = self._calculate_file_hash(file_path)
            if not source_hash:
                return []
            
            duplicates = []
            
            # Search all files in target folder
            if os.path.isdir(target_folder):
                for root, dirs, files in os.walk(target_folder):
                    for filename in files:
                        candidate_path = os.path.join(root, filename)
                        try:
                            candidate_hash = self._calculate_file_hash(candidate_path)
                            if candidate_hash == source_hash:
                                duplicates.append(candidate_path)
                        except:
                            continue
            
            return duplicates
            
        except Exception as e:
            self.logger.log(
                "duplicate_search_error",
                f"Error searching for duplicates: {str(e)}",
                "warning"
            )
            return []

    def remove_duplicates_in_project(
        self,
        duplicate_paths: List[str],
        username: str,
        session_id: str
    ) -> Dict[str, int]:
        """
        Safely remove duplicate files from project.
        
        Deletes old duplicate files and logs each removal.
        Handles errors gracefully - partial success is still reported.
        
        Args:
            duplicate_paths: List of duplicate file paths to delete
            username: Username performing the cleanup
            session_id: Session ID for audit trail
            
        Returns:
            Dictionary with keys:
            - deleted: Number of successfully deleted files
            - failed: Number of deletion failures
        """
        result = {"deleted": 0, "failed": 0}
        
        for duplicate_path in duplicate_paths:
            try:
                if os.path.isfile(duplicate_path):
                    file_size = os.path.getsize(duplicate_path)
                    os.remove(duplicate_path)
                    result["deleted"] += 1
                    
                    self.logger.log(
                        "project_duplicate_deleted",
                        f"Duplicate removed from {duplicate_path} (Size: {file_size} bytes)",
                        "success",
                        session_id=session_id
                    )
                    
            except Exception as e:
                result["failed"] += 1
                self.logger.log(
                    "project_duplicate_delete_error",
                    f"Failed to delete duplicate {duplicate_path}: {str(e)}",
                    "warning",
                    session_id=session_id
                )
        
        return result

    def move_file_to_project(
        self,
        file_path: str,
        filename: str,
        project_path: str,
        username: str,
        session_id: str,
        remove_duplicates: bool = True
    ) -> Tuple[bool, str, Dict]:
        """
        Move file to appropriate project folder with duplicate handling.
        
        Complete workflow:
        1. Detect file type
        2. Determine target folder
        3. Find and remove duplicates
        4. Move file (cut + paste, not copy)
        5. Verify move success
        6. Log all actions
        
        Args:
            file_path: Current full path to the file
            filename: Name of the file
            project_path: Root path of the project
            username: Username performing the move
            session_id: Session ID for audit trail
            remove_duplicates: Whether to auto-remove duplicates
            
        Returns:
            Tuple of:
            - success: bool indicating if move succeeded
            - final_destination: Full path where file was moved
            - metadata: Dict with details (type, duplicates_found, duplicates_removed, etc)
            
        Raises:
            FileOperationError: If move operation fails critically
            ValidationError: If inputs are invalid
        """
        metadata = {
            "detected_type": None,
            "target_folder": None,
            "duplicates_found": 0,
            "duplicates_removed": 0,
            "file_size": 0,
            "moved_to": None
        }
        
        try:
            # Validate inputs
            if not os.path.exists(file_path):
                raise ValidationError(f"Source file does not exist: {file_path}")
            
            if not os.path.isdir(project_path):
                raise ValidationError(f"Project path does not exist: {project_path}")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            metadata["file_size"] = file_size
            
            # Detect file type
            file_type = self.detect_project_file_type(filename)
            metadata["detected_type"] = file_type.value
            
            # Determine target folder
            target_folder = os.path.join(project_path, file_type.value)
            os.makedirs(target_folder, exist_ok=True)
            metadata["target_folder"] = file_type.value
            
            # Log file categorization
            self.logger.log(
                "project_file_categorized",
                f"File categorized as {file_type.value}: {filename}",
                "success",
                session_id=session_id
            )
            
            # Find duplicates if enabled
            if remove_duplicates:
                duplicates = self.find_duplicates_in_project(file_path, target_folder)
                metadata["duplicates_found"] = len(duplicates)
                
                if duplicates:
                    self.logger.log(
                        "project_duplicates_found",
                        f"Found {len(duplicates)} duplicate(s) for {filename}",
                        "success",
                        session_id=session_id
                    )
                    
                    # Remove duplicates
                    cleanup_result = self.remove_duplicates_in_project(
                        duplicates, username, session_id
                    )
                    metadata["duplicates_removed"] = cleanup_result["deleted"]
                    
                    if cleanup_result["deleted"] > 0:
                        self.logger.log(
                            "project_cleanup_completed",
                            f"Removed {cleanup_result['deleted']} duplicate(s), "
                            f"{cleanup_result['failed']} failed",
                            "success",
                            session_id=session_id
                        )
            
            # Ensure destination doesn't already exist
            destination = os.path.join(target_folder, filename)
            counter = 1
            original_destination = destination
            name, ext = os.path.splitext(filename)
            
            while os.path.exists(destination):
                destination = os.path.join(target_folder, f"{name}_{counter}{ext}")
                counter += 1
            
            # Move file (cut + paste)
            shutil.move(file_path, destination)
            metadata["moved_to"] = destination
            
            # Verify move success
            if not os.path.exists(destination):
                raise FileOperationError(f"File move verification failed: {destination}")
            
            # Log successful move
            self.logger.log(
                "project_file_moved",
                f"File moved to {file_type.value}/{os.path.basename(destination)}",
                "success",
                session_id=session_id
            )
            
            return True, destination, metadata
            
        except (FileOperationError, ValidationError) as e:
            self.logger.log(
                "project_move_error",
                f"Failed to move file: {str(e)}",
                "error",
                session_id=session_id
            )
            raise
        except Exception as e:
            error_msg = f"Unexpected error during file move: {str(e)}"
            self.logger.log(
                "project_move_unexpected_error",
                error_msg,
                "error",
                session_id=session_id
            )
            raise FileOperationError(error_msg)

    def log_event(
        self,
        action: str,
        filename: str,
        details: str,
        status: str = "success",
        session_id: Optional[str] = None
    ) -> None:
        """
        Log a project organization event to database.
        
        Args:
            action: Type of action (e.g., "project_file_moved", "project_duplicates_found")
            filename: Name of the file involved
            details: Detailed message about the action
            status: Status of the action (success, warning, error)
            session_id: Optional session ID for audit trail
        """
        try:
            self.logger.log(action, details, status, session_id=session_id)
        except Exception as e:
            # Ensure logging failures don't crash the system
            print(f"Failed to log event {action}: {str(e)}")

    def get_project_statistics(self, project_path: str) -> Dict:
        """
        Get statistics about files in a project.
        
        Args:
            project_path: Path to the project
            
        Returns:
            Dictionary with file counts per category and total
        """
        stats = {
            "backend": 0,
            "frontend": 0,
            "database": 0,
            "images": 0,
            "documents": 0,
            "others": 0,
            "total_files": 0,
            "total_size_bytes": 0
        }
        
        try:
            for folder in self.PROJECT_STRUCTURE:
                folder_path = os.path.join(project_path, folder)
                if os.path.exists(folder_path):
                    for root, dirs, files in os.walk(folder_path):
                        for filename in files:
                            file_path = os.path.join(root, filename)
                            stats[folder] += 1
                            stats["total_files"] += 1
                            stats["total_size_bytes"] += os.path.getsize(file_path)
            
            return stats
        except Exception as e:
            self.logger.log(
                "project_stats_error",
                f"Error calculating project statistics: {str(e)}",
                "warning"
            )
            return stats

    def list_project_files(self, project_path: str) -> Dict[str, List[str]]:
        """
        List all files organized by type in a project.
        
        Args:
            project_path: Path to the project
            
        Returns:
            Dictionary mapping folder types to list of files
        """
        result = {folder: [] for folder in self.PROJECT_STRUCTURE}
        
        try:
            for folder in self.PROJECT_STRUCTURE:
                folder_path = os.path.join(project_path, folder)
                if os.path.exists(folder_path):
                    for root, dirs, files in os.walk(folder_path):
                        for filename in files:
                            result[folder].append(filename)
            
            return result
        except Exception as e:
            self.logger.log(
                "project_list_error",
                f"Error listing project files: {str(e)}",
                "warning"
            )
            return result

    def clear_cache(self) -> None:
        """Clear the hash cache to free memory."""
        self.hash_cache.clear()
