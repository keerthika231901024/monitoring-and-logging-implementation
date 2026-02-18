from datetime import datetime


class LogManager:
    def __init__(self, db_manager, log_file_path):
        self.db = db_manager
        self.log_file_path = log_file_path

    def log(self, username, action, filename, status, message, session_id):
        timestamp = datetime.utcnow().isoformat()
        self.db.add_log(username, action, filename, status, message, session_id)
        log_line = (
            f"{timestamp} | {session_id} | {username} | {action} | {filename} | {status} | {message}\n"
        )
        with open(self.log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_line)
