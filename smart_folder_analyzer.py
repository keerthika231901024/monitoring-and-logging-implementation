import os
import shutil
import hashlib


class SmartFolderAnalyzer:
    """Analyze a folder for duplicates, unwanted, empty, and large files."""

    def __init__(self, logger):
        self.logger = logger
        self.unwanted_extensions = {".tmp", ".log", ".cache"}

    def _calculate_file_hash(self, file_path):
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as file_handle:
                for chunk in iter(lambda: file_handle.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception:
            return None

    def scan_folder(self, folder_path, include_large=False, large_size_mb=50):
        """Scan a folder recursively and return analysis results."""
        results = {
            "folder_path": folder_path,
            "total_files": 0,
            "duplicate_files": [],
            "duplicate_count": 0,
            "unwanted_files": [],
            "unwanted_count": 0,
            "empty_files": [],
            "empty_count": 0,
            "large_files": [],
            "large_count": 0,
        }

        if not os.path.isdir(folder_path):
            return results

        name_seen = {}
        hash_seen = {}
        duplicate_set = set()
        large_threshold_bytes = large_size_mb * 1024 * 1024

        for root, _, files in os.walk(folder_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                if not os.path.isfile(file_path):
                    continue

                results["total_files"] += 1

                try:
                    file_size = os.path.getsize(file_path)
                except Exception:
                    file_size = 0

                if file_size == 0:
                    results["empty_files"].append(file_path)

                if include_large and file_size > large_threshold_bytes:
                    results["large_files"].append(file_path)

                _, ext = os.path.splitext(filename)
                if ext.lower() in self.unwanted_extensions:
                    results["unwanted_files"].append(file_path)

                if filename in name_seen:
                    duplicate_set.add(file_path)
                else:
                    name_seen[filename] = file_path

                file_hash = self._calculate_file_hash(file_path)
                if file_hash:
                    if file_hash in hash_seen and hash_seen[file_hash] != file_path:
                        duplicate_set.add(file_path)
                    else:
                        hash_seen[file_hash] = file_path

        results["duplicate_files"] = sorted(duplicate_set)
        results["duplicate_count"] = len(results["duplicate_files"])
        results["unwanted_count"] = len(results["unwanted_files"])
        results["empty_count"] = len(results["empty_files"])
        results["large_count"] = len(results["large_files"])

        return results

    def clean_folder(self, folder_path, username, session_id, include_large=False, large_size_mb=50):
        """Delete duplicate copies only, keeping one original file."""
        results = self.scan_folder(folder_path, include_large, large_size_mb)
        deleted_files = []
        failed_files = []

        delete_targets = set(results["duplicate_files"])

        for file_path in sorted(delete_targets):
            try:
                if not os.path.isfile(file_path):
                    continue

                os.remove(file_path)

                deleted_files.append(file_path)
                self.logger.log(
                    username,
                    "smart_folder_delete",
                    os.path.basename(file_path),
                    "success",
                    f"Deleted duplicate: {file_path}",
                    session_id,
                )
            except Exception as exc:
                failed_files.append(file_path)
                self.logger.log(
                    username,
                    "smart_folder_delete_error",
                    os.path.basename(file_path),
                    "error",
                    f"Failed to delete duplicate {file_path}: {str(exc)}",
                    session_id,
                )

        cleanup_summary = {
            "deleted_count": len(deleted_files),
            "failed_count": len(failed_files),
            "deleted_files": deleted_files,
            "failed_files": failed_files,
        }

        return results, cleanup_summary
