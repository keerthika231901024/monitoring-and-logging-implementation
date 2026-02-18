import os
import random
import string
import shutil
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory

from auth_manager import UserAuth
from database_manager import DatabaseManager
from logger import LogManager
from organizer import FileOrganizer
from project_organizer import SmartProjectOrganizer
from system_monitor import SystemMonitor
from file_monitor import FileMonitor
from file_manager import FileManager
from exceptions import AppError


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
TEMP_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "temp")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["TEMP_UPLOAD_FOLDER"] = TEMP_UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)


db = DatabaseManager(os.path.join(BASE_DIR, "app.db"))
logger = LogManager(db, os.path.join(BASE_DIR, "log.txt"))
auth = UserAuth(db, logger)
organizer = FileOrganizer(logger)
project_organizer = SmartProjectOrganizer(logger)
monitor = SystemMonitor(db, logger)
file_monitor = FileMonitor(logger)
file_manager = FileManager(logger, db)


db.initialize()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def ensure_session_id():
    if "session_id" not in session:
        session["session_id"] = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    return session["session_id"]


def resolve_upload_destination(folder_path, filename):
    name, ext = os.path.splitext(filename)
    destination = os.path.join(folder_path, filename)
    counter = 1
    while os.path.exists(destination):
        destination = os.path.join(folder_path, f"{name}_{counter}{ext}")
        counter += 1
    return destination


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            user = auth.authenticate_user(username, password)
            if not user:
                flash("Invalid username or password.", "error")
                return redirect(url_for("login"))
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            ensure_session_id()
            logger.log(
                username,
                "login",
                "-",
                "success",
                f"User {username} logged in",
                session["session_id"],
            )
            return redirect(url_for("dashboard"))
        except AppError as exc:
            flash(str(exc), "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            auth.register_user(username, password)
            logger.log(
                username,
                "register",
                "-",
                "success",
                f"User {username} registered",
                ensure_session_id(),
            )
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except AppError as exc:
            flash(str(exc), "error")
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    username = session.get("username", "unknown")
    session_id = session.get("session_id", "-")
    session.clear()
    logger.log(username, "logout", "-", "success", f"User {username} logged out", session_id)
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    session_id = ensure_session_id()
    username = session.get("username", "")
    stats = monitor.get_latest_stats(username, session_id)
    logs = db.get_recent_logs(username, limit=10)
    pending_uploads = db.get_pending_uploads(username, limit=10)
    organized_logs = db.get_logs_by_action(username, "uploaded_and_organized", limit=10)
    delete_logs = db.get_logs_by_action(username, "delete", limit=10)
    monitoring_logs = db.get_monitoring_logs(username, limit=10)
    system_status = monitor.get_system_status(stats)
    is_monitoring = file_monitor.is_monitoring(username, session_id)
    event_count = file_monitor.get_event_count(username, session_id)
    monitored_folder = session.get("monitored_folder", "No folder selected")
    return render_template(
        "dashboard.html",
        stats=stats,
        logs=logs,
        pending_uploads=pending_uploads,
        organized_logs=organized_logs,
        delete_logs=delete_logs,
        monitoring_logs=monitoring_logs,
        system_status=system_status,
        session_id=session_id,
        is_monitoring=is_monitoring,
        event_count=event_count,
        monitored_folder=monitored_folder,
    )


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    session_id = ensure_session_id()
    username = session.get("username", "")
    upload_file = request.files.get("file")

    if not upload_file or not upload_file.filename:
        flash("Select a file to upload.", "error")
        return redirect(url_for("dashboard"))

    try:
        safe_name = os.path.basename(upload_file.filename)
        
        # Save temporarily to temp uploads folder
        temp_folder = app.config["TEMP_UPLOAD_FOLDER"]
        os.makedirs(temp_folder, exist_ok=True)
        temp_destination = resolve_upload_destination(temp_folder, safe_name)
        upload_file.save(temp_destination)
        
        # Get file categorization info
        file_info = organizer.get_file_destination_info(safe_name)
        
        # Log the upload for confirmation
        logger.log(
            username,
            "upload_pending",
            safe_name,
            "success",
            f"File uploaded. Waiting for user confirmation to organize to {file_info['category']}",
            session_id,
        )
        
        flash(f"File uploaded successfully! Do you want to organize it to {file_info['category']} folder?", "info")
            
    except Exception as exc:
        logger.log(
            username,
            "upload",
            upload_file.filename if upload_file else "-",
            "error",
            f"Upload failed: {exc}",
            session_id,
        )
        flash("Upload failed. Check logs for details.", "error")

    return redirect(url_for("dashboard"))


@app.route("/organize", methods=["GET", "POST"])
@login_required
def organize():
    session_id = ensure_session_id()
    username = session.get("username", "")
    summary = None

    if request.method == "POST":
        folder_path = request.form.get("folder_path", "").strip()
        uploaded_files = request.files.getlist("files")
        try:
            if uploaded_files and any(file.filename for file in uploaded_files):
                upload_session_dir = os.path.join(app.config["UPLOAD_FOLDER"], session_id)
                os.makedirs(upload_session_dir, exist_ok=True)
                for file in uploaded_files:
                    if not file.filename:
                        continue
                    safe_name = os.path.basename(file.filename)
                    file.save(os.path.join(upload_session_dir, safe_name))
                summary = organizer.organize_folder(upload_session_dir, session_id, username)
            elif folder_path:
                summary = organizer.organize_folder(folder_path, session_id, username)
            else:
                flash("Provide a folder path or upload files.", "error")

            if summary:
                monitor.record_run(
                    username,
                    summary["total_files"],
                    summary["total_errors"],
                    session_id,
                )
                flash(
                    f"Processed {summary['total_files']} files with {summary['total_errors']} errors.",
                    "success" if summary["total_errors"] == 0 else "warning",
                )
        except AppError as exc:
            logger.log(username, "organize", folder_path or "uploads", "error", str(exc), session_id)
            flash(str(exc), "error")
        except Exception as exc:
            logger.log(
                username,
                "organize",
                folder_path or "uploads",
                "error",
                f"Unexpected error: {exc}",
                session_id,
            )
            flash("Unexpected error occurred. Check logs for details.", "error")

    return render_template("organize.html", summary=summary)


@app.route("/logs")
@login_required
def logs():
    session_id = ensure_session_id()
    username = session.get("username", "")
    stats = monitor.get_latest_stats(username, session_id)
    logs = db.get_recent_logs(username, limit=50)
    system_status = monitor.get_system_status(stats)
    return render_template(
        "logs.html",
        logs=logs,
        stats=stats,
        system_status=system_status,
        session_id=session_id,
    )


@app.route("/view_file/<filename>")
@login_required
def view_file(filename):
    session_id = ensure_session_id()
    username = session.get("username", "")
    
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
    
    try:
        # Verify ownership and log access
        file_manager.log_file_access(username, safe_filename, "view", session_id)
        
        # Check if file exists
        if not os.path.exists(file_path):
            flash("File not found.", "error")
            return redirect(url_for("dashboard"))
        
        # Serve file inline (view in browser)
        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            safe_filename,
            as_attachment=False
        )
    except AppError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))
    except Exception as exc:
        flash("Error accessing file.", "error")
        logger.log(
            username,
            "view",
            safe_filename,
            "error",
            f"Unexpected error: {exc}",
            session_id,
        )
        return redirect(url_for("dashboard"))


@app.route("/download_file/<filename>")
@login_required
def download_file(filename):
    session_id = ensure_session_id()
    username = session.get("username", "")
    
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
    
    try:
        # Verify ownership and log access
        file_manager.log_file_access(username, safe_filename, "download", session_id)
        
        # Check if file exists
        if not os.path.exists(file_path):
            flash("File not found.", "error")
            return redirect(url_for("dashboard"))
        
        # Serve file as download
        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            safe_filename,
            as_attachment=True,
            download_name=safe_filename
        )
    except AppError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))
    except Exception as exc:
        flash("Error downloading file.", "error")
        logger.log(
            username,
            "download",
            safe_filename,
            "error",
            f"Unexpected error: {exc}",
            session_id,
        )
        return redirect(url_for("dashboard"))


@app.route("/delete_file/<filename>", methods=["POST"])
@login_required
def delete_file(filename):
    session_id = ensure_session_id()
    username = session.get("username", "")
    
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
    
    try:
        result = file_manager.delete_file(username, safe_filename, file_path, session_id)
        flash(result["message"], "success")
    except AppError as exc:
        flash(str(exc), "error")
    
    return redirect(url_for("dashboard"))


@app.route("/confirm_organize/<filename>", methods=["POST"])
@login_required
def confirm_organize(filename):
    """User confirmed: organize the file to system folder with automatic system-wide duplicate removal."""
    session_id = ensure_session_id()
    username = session.get("username", "")
    
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    temp_file_path = os.path.join(app.config["TEMP_UPLOAD_FOLDER"], safe_filename)
    
    try:
        if not os.path.exists(temp_file_path):
            flash(f"File not found: {safe_filename}", "error")
            return redirect(url_for("dashboard"))
        
        # Organize to system folders (with automatic system-wide duplicate detection and removal)
        result = organizer.confirm_organization(
            temp_file_path,
            safe_filename,
            session_id,
            username
        )
        
        if result["success"]:
            # Use the message from organizer which includes system-wide cleanup details
            message = result.get("message", f"✓ {safe_filename} organized successfully")
            
            # Enhance message with additional cleanup details if available
            system_wide_removed = result.get("system_wide_duplicates_removed", 0)
            total_removed = result.get("total_duplicates_removed", 0)
            
            # If organizer didn't provide formatted message, build it here
            if message == f"{safe_filename} moved to {result.get('category', '?')} folder":
                if total_removed > 0:
                    if system_wide_removed > 0:
                        message = f"✓ {safe_filename} moved to {result.get('category', 'correct')} folder • {total_removed} old copies removed from system"
                    else:
                        destination_removed = result.get("duplicates_removed", 0)
                        if destination_removed > 0:
                            message = f"✓ {safe_filename} moved to {result.get('category', 'correct')} folder • {destination_removed} duplicate(s) removed"
            
            # Add emoji for visual feedback
            if not message.startswith("✓"):
                message = f"✓ {message}"
            
            flash(message, "success")
            
            # Log final success with system-wide cleanup details
            logger.log(
                username,
                "file_organization_confirmed",
                safe_filename,
                "success",
                f"File successfully organized: {message} | System-wide duplicates: {system_wide_removed} | Total removed: {total_removed}",
                session_id,
            )
        else:
            error_msg = result.get("error", "Unknown error")
            flash(f"Organization failed: {error_msg}", "error")
            logger.log(
                username,
                "organization_failed",
                safe_filename,
                "error",
                f"Organization failed: {error_msg}",
                session_id,
            )
            
    except Exception as exc:
        logger.log(
            username,
            "organize_error",
            safe_filename,
            "error",
            f"Unexpected error: {str(exc)}",
            session_id,
        )
        flash("Organization failed. Check logs for details.", "error")
    
    return redirect(url_for("dashboard"))


@app.route("/reject_organize/<filename>", methods=["POST"])
@login_required
def reject_organize(filename):
    """User rejected organization: ensure file is removed from temp folder."""
    session_id = ensure_session_id()
    username = session.get("username", "")
    
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    temp_file_path = os.path.join(app.config["TEMP_UPLOAD_FOLDER"], safe_filename)
    
    try:
        if not os.path.exists(temp_file_path):
            flash(f"File not found: {safe_filename}", "error")
            return redirect(url_for("dashboard"))
        
        # Delete file from temp folder (cleanup)
        try:
            os.remove(temp_file_path)
            message = f"{safe_filename} removed from upload folder"
            
            # Log the action
            result = organizer.reject_organization(
                safe_filename,
                session_id,
                username
            )
            
            # Log successful cleanup
            logger.log(
                username,
                "upload_rejected_and_deleted",
                safe_filename,
                "success",
                f"File rejected and deleted from temp folder",
                session_id,
            )
            
            flash(message, "info")
            
        except Exception as delete_exc:
            logger.log(
                username,
                "reject_delete_failed",
                safe_filename,
                "error",
                f"Failed to delete rejected file: {str(delete_exc)}",
                session_id,
            )
            flash(f"Failed to delete file. Error: {str(delete_exc)}", "error")
            
    except Exception as exc:
        logger.log(
            username,
            "reject_organize_error",
            safe_filename,
            "error",
            f"Failed to process rejection: {str(exc)}",
            session_id,
        )
        flash("Failed to process rejection. Check logs for details.", "error")
    
    return redirect(url_for("dashboard"))


@app.route("/start_monitoring", methods=["POST"])
@login_required
def start_monitoring():
    session_id = ensure_session_id()
    username = session.get("username", "")
    folder_path = request.form.get("folder_path", "").strip()

    if not folder_path:
        flash("Provide a folder path to monitor.", "error")
        return redirect(url_for("dashboard"))

    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        flash("Invalid folder path.", "error")
        return redirect(url_for("dashboard"))

    try:
        file_monitor.start_monitoring(username, session_id, folder_path)
        session["monitored_folder"] = folder_path
        flash(f"Monitoring started for: {folder_path}", "success")
    except Exception as exc:
        logger.log(
            username,
            "monitoring_error",
            folder_path,
            "error",
            f"Failed to start monitoring: {exc}",
            session_id,
        )
        flash("Failed to start monitoring. Check logs.", "error")

    return redirect(url_for("dashboard"))


@app.route("/stop_monitoring", methods=["POST"])
@login_required
def stop_monitoring():
    session_id = ensure_session_id()
    username = session.get("username", "")

    try:
        file_monitor.stop_monitoring(username, session_id)
        session["monitored_folder"] = "No folder selected"
        flash("Monitoring stopped.", "success")
    except Exception as exc:
        logger.log(
            username,
            "monitoring_error",
            "-",
            "error",
            f"Failed to stop monitoring: {exc}",
            session_id,
        )
        flash("Failed to stop monitoring.", "error")

    return redirect(url_for("dashboard"))


# ===== PROJECT-BASED SMART FILE ORGANIZATION ROUTES =====

@app.route("/projects")
@login_required
def projects():
    """Display all projects for the current user."""
    username = session.get("username")
    session_id = ensure_session_id()
    
    try:
        user_projects = db.get_user_projects(username)
        
        # Add statistics for each project
        for project in user_projects:
            project_id = project["id"]
            project_path = project["project_path"]
            
            # Get project statistics
            stats = project_organizer.get_project_statistics(project_path)
            project["stats"] = stats
            
            # Get file list
            files = project_organizer.list_project_files(project_path)
            project["files"] = files
        
        logger.log(
            "projects_viewed",
            f"Viewed projects list ({len(user_projects)} projects)",
            "success",
            session_id=session_id
        )
        
        return render_template("projects.html", projects=user_projects)
        
    except Exception as exc:
        logger.log(
            "projects_view_error",
            f"Failed to load projects: {str(exc)}",
            "error",
            session_id=session_id
        )
        flash("Failed to load projects.", "error")
        return redirect(url_for("dashboard"))


@app.route("/project/create", methods=["GET", "POST"])
@login_required
def create_project():
    """Create a new development project."""
    username = session.get("username")
    session_id = ensure_session_id()
    
    if request.method == "POST":
        project_name = request.form.get("project_name", "").strip()
        
        if not project_name:
            flash("Project name cannot be empty.", "error")
            return render_template("create_project.html")
        
        try:
            # Create project structure
            success, project_path = project_organizer.create_project_structure(project_name)
            
            if success:
                # Save to database
                project_id = db.create_project(username, project_name, project_path)
                
                logger.log(
                    "project_created",
                    f"New project created: {project_name} at {project_path}",
                    "success",
                    session_id=session_id
                )
                
                flash(f"Project '{project_name}' created successfully at {project_path}", "success")
                return redirect(url_for("view_project", project_id=project_id))
            else:
                flash("Failed to create project structure.", "error")
                
        except Exception as exc:
            logger.log(
                "project_creation_error",
                f"Failed to create project: {str(exc)}",
                "error",
                session_id=session_id
            )
            flash(f"Error creating project: {str(exc)}", "error")
    
    return render_template("create_project.html")


@app.route("/project/<int:project_id>")
@login_required
def view_project(project_id):
    """View a specific project and its organized files."""
    username = session.get("username")
    session_id = ensure_session_id()
    
    try:
        project = db.get_project_by_id(project_id)
        
        if not project or project["username"] != username:
            flash("Project not found or access denied.", "error")
            return redirect(url_for("projects"))
        
        # Get project statistics
        project_path = project["project_path"]
        stats = project_organizer.get_project_statistics(project_path)
        files = project_organizer.list_project_files(project_path)
        project_files = db.get_project_files(project_id)
        file_stats = db.get_project_file_statistics(project_id)
        
        logger.log(
            "project_viewed",
            f"Viewed project: {project['project_name']}",
            "success",
            session_id=session_id
        )
        
        return render_template(
            "view_project.html",
            project=project,
            stats=stats,
            files=files,
            project_files=project_files,
            file_stats=file_stats
        )
        
    except Exception as exc:
        logger.log(
            "project_view_error",
            f"Failed to view project: {str(exc)}",
            "error",
            session_id=session_id
        )
        flash("Failed to view project.", "error")
        return redirect(url_for("projects"))


@app.route("/project/<int:project_id>/upload", methods=["POST"])
@login_required
def project_upload(project_id):
    """Upload file to project with automatic organization."""
    username = session.get("username")
    session_id = ensure_session_id()
    
    try:
        project = db.get_project_by_id(project_id)
        
        if not project or project["username"] != username:
            return {"error": "Project not found or access denied"}, 403
        
        if "file" not in request.files:
            return {"error": "No file provided"}, 400
        
        uploaded_file = request.files["file"]
        if uploaded_file.filename == "":
            return {"error": "No file selected"}, 400
        
        # Save uploaded file temporarily
        filename = uploaded_file.filename
        temp_path = os.path.join(TEMP_UPLOAD_FOLDER, filename)
        uploaded_file.save(temp_path)
        
        logger.log(
            "project_upload_pending",
            f"File uploaded to project {project['project_name']}: {filename}",
            "success",
            session_id=session_id
        )
        
        # Move file to project with duplicate handling
        try:
            success, destination, metadata = project_organizer.move_file_to_project(
                temp_path, filename, project["project_path"],
                username, session_id, remove_duplicates=True
            )
            
            if success:
                # Track file in database
                db.add_project_file(
                    project_id, filename,
                    metadata["detected_type"],
                    temp_path,
                    destination,
                    metadata["file_size"],
                    metadata["duplicates_removed"],
                    project_organizer._calculate_file_hash(destination)
                )
                
                db.update_project_file_count(project_id)
                
                logger.log(
                    "project_file_organized",
                    f"File organized: {filename} → {metadata['detected_type']} "
                    f"(Duplicates removed: {metadata['duplicates_removed']})",
                    "success",
                    session_id=session_id
                )
                
                return {
                    "success": True,
                    "filename": filename,
                    "file_type": metadata["detected_type"],
                    "destination": os.path.basename(destination),
                    "duplicates_removed": metadata["duplicates_removed"],
                    "file_size": metadata["file_size"]
                }, 200
            else:
                return {"error": "Failed to organize file"}, 500
                
        except Exception as exc:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            logger.log(
                "project_file_organization_error",
                f"Failed to organize file: {str(exc)}",
                "error",
                session_id=session_id
            )
            return {"error": f"Organization failed: {str(exc)}"}, 500
        
    except Exception as exc:
        logger.log(
            "project_upload_error",
            f"Failed to upload to project: {str(exc)}",
            "error",
            session_id=session_id
        )
        return {"error": f"Upload failed: {str(exc)}"}, 500


@app.route("/project/<int:project_id>/monitor", methods=["POST"])
@login_required
def project_monitor(project_id):
    """Enable/disable monitoring for a project folder."""
    username = session.get("username")
    session_id = ensure_session_id()
    
    try:
        project = db.get_project_by_id(project_id)
        
        if not project or project["username"] != username:
            flash("Project not found or access denied.", "error")
            return redirect(url_for("projects"))
        
        should_monitor = request.form.get("monitor") == "true"
        db.update_project_monitoring(project_id, 1 if should_monitor else 0)
        
        action = "started" if should_monitor else "stopped"
        logger.log(
            "project_monitoring_updated",
            f"Project monitoring {action}: {project['project_name']}",
            "success",
            session_id=session_id
        )
        
        flash(f"Project monitoring {action}.", "success")
        return redirect(url_for("view_project", project_id=project_id))
        
    except Exception as exc:
        logger.log(
            "project_monitor_error",
            f"Failed to update monitoring: {str(exc)}",
            "error",
            session_id=session_id
        )
        flash("Failed to update monitoring status.", "error")
        return redirect(url_for("view_project", project_id=project_id))


@app.route("/project/<int:project_id>/statistics")
@login_required
def project_statistics(project_id):
    """Get detailed statistics for a project."""
    username = session.get("username")
    
    try:
        project = db.get_project_by_id(project_id)
        
        if not project or project["username"] != username:
            return {"error": "Project not found or access denied"}, 403
        
        project_path = project["project_path"]
        stats = project_organizer.get_project_statistics(project_path)
        file_stats = db.get_project_file_statistics(project_id)
        
        return {
            "project_name": project["project_name"],
            "total_files": stats["total_files"],
            "total_size_bytes": stats["total_size_bytes"],
            "by_type": {
                folder: {
                    "count": stats[folder],
                    "size_bytes": stats.get(f"{folder}_size", 0)
                }
                for folder in project_organizer.PROJECT_STRUCTURE
            },
            "file_stats": file_stats
        }, 200
        
    except Exception as exc:
        return {"error": f"Failed to get statistics: {str(exc)}"}, 500


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("error.html", message="Page not found."), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", message="Internal server error."), 500


if __name__ == "__main__":
    try:
        app.run(debug=True)
    finally:
        file_monitor.stop_all()
