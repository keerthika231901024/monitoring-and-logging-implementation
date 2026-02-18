from datetime import datetime


class SystemMonitor:
    def __init__(self, db_manager, logger):
        self.db = db_manager
        self.logger = logger

    def record_run(self, username, total_files, total_errors, session_id):
        self.db.update_stats(username, total_files, total_errors, session_id)
        self.logger.log(
            username,
            "system_run",
            "-",
            "success" if total_errors == 0 else "warning",
            f"Run completed. Files: {total_files}, Errors: {total_errors}",
            session_id,
        )

    def get_latest_stats(self, username, session_id):
        stats = self.db.get_latest_stats(username)
        if not stats:
            return {
                "total_files": 0,
                "total_errors": 0,
                "last_run": "-",
                "session_id": session_id,
                "username": username,
            }
        return stats

    def get_system_status(self, stats):
        if not stats:
            return "Unknown"
        if stats["total_errors"] == 0:
            return "Healthy"
        if stats["total_errors"] < 3:
            return "Degraded"
        return "Attention Required"
