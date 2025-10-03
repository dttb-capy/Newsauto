"""Cron job management for scheduled tasks."""

import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CronManager:
    """Manages cron jobs for newsletter automation."""

    def __init__(self, project_path: str = None):
        """Initialize cron manager.

        Args:
            project_path: Path to project directory
        """
        self.project_path = project_path or Path.cwd()
        self.python_path = "python3"
        self.cron_identifier = "# Newsauto"

    def list_jobs(self) -> List[str]:
        """List current cron jobs.

        Returns:
            List of cron job lines
        """
        try:
            result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, check=False
            )

            if result.returncode == 0:
                return result.stdout.strip().split("\n")
            else:
                return []

        except Exception as e:
            logger.error(f"Error listing cron jobs: {e}")
            return []

    def add_job(self, schedule: str, command: str, comment: str = None) -> bool:
        """Add a cron job.

        Args:
            schedule: Cron schedule (e.g., "0 9 * * *")
            command: Command to run
            comment: Optional comment

        Returns:
            Success status
        """
        try:
            # Get existing jobs
            jobs = self.list_jobs()

            # Create new job line
            job_line = f"{schedule} {command}"
            if comment:
                job_line += f" {self.cron_identifier} {comment}"
            else:
                job_line += f" {self.cron_identifier}"

            # Check if job already exists
            if any(schedule in job and command in job for job in jobs):
                logger.warning("Job already exists")
                return False

            # Add new job
            jobs.append(job_line)

            # Update crontab
            return self._update_crontab(jobs)

        except Exception as e:
            logger.error(f"Error adding cron job: {e}")
            return False

    def remove_job(self, identifier: str) -> bool:
        """Remove a cron job.

        Args:
            identifier: Job identifier (command or comment)

        Returns:
            Success status
        """
        try:
            jobs = self.list_jobs()
            filtered_jobs = [job for job in jobs if identifier not in job]

            if len(filtered_jobs) == len(jobs):
                logger.warning("Job not found")
                return False

            return self._update_crontab(filtered_jobs)

        except Exception as e:
            logger.error(f"Error removing cron job: {e}")
            return False

    def _update_crontab(self, jobs: List[str]) -> bool:
        """Update crontab with new jobs.

        Args:
            jobs: List of job lines

        Returns:
            Success status
        """
        try:
            # Create temp crontab content
            crontab_content = "\n".join(jobs) + "\n"

            # Update crontab
            process = subprocess.Popen(
                ["crontab", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = process.communicate(input=crontab_content)

            if process.returncode == 0:
                logger.info("Crontab updated successfully")
                return True
            else:
                logger.error(f"Error updating crontab: {stderr}")
                return False

        except Exception as e:
            logger.error(f"Error updating crontab: {e}")
            return False

    def setup_newsauto_jobs(self) -> bool:
        """Set up all Newsauto cron jobs.

        Returns:
            Success status
        """
        jobs = [
            # Fetch content every hour
            {
                "schedule": "0 * * * *",
                "command": f"cd {self.project_path} && {self.python_path} -m newsauto.cli fetch-content",
                "comment": "Fetch content hourly",
            },
            # Process scheduled newsletters
            {
                "schedule": "*/5 * * * *",
                "command": f"cd {self.project_path} && {self.python_path} -m newsauto.cli process-scheduled",
                "comment": "Process scheduled sends",
            },
            # Daily maintenance
            {
                "schedule": "0 3 * * *",
                "command": f"cd {self.project_path} && {self.python_path} -m newsauto.cli daily-maintenance",
                "comment": "Daily maintenance tasks",
            },
            # Weekly analytics
            {
                "schedule": "0 9 * * 1",
                "command": f"cd {self.project_path} && {self.python_path} -m newsauto.cli generate-report",
                "comment": "Weekly analytics report",
            },
        ]

        success = True
        for job in jobs:
            if not self.add_job(job["schedule"], job["command"], job["comment"]):
                success = False
                logger.error(f"Failed to add job: {job['comment']}")

        return success

    def remove_newsauto_jobs(self) -> bool:
        """Remove all Newsauto cron jobs.

        Returns:
            Success status
        """
        try:
            jobs = self.list_jobs()
            filtered_jobs = [job for job in jobs if self.cron_identifier not in job]

            return self._update_crontab(filtered_jobs)

        except Exception as e:
            logger.error(f"Error removing Newsauto jobs: {e}")
            return False

    def validate_cron_syntax(self, schedule: str) -> bool:
        """Validate cron schedule syntax.

        Args:
            schedule: Cron schedule string

        Returns:
            Validation status
        """
        parts = schedule.split()
        if len(parts) != 5:
            return False

        # Basic validation
        ranges = [
            (0, 59),  # minute
            (0, 23),  # hour
            (1, 31),  # day of month
            (1, 12),  # month
            (0, 6),  # day of week
        ]

        for i, part in enumerate(parts):
            if part == "*":
                continue

            if "/" in part:
                # Step values
                base, step = part.split("/")
                if base != "*" and not self._validate_range(base, *ranges[i]):
                    return False
                if not step.isdigit():
                    return False

            elif "," in part:
                # List of values
                for val in part.split(","):
                    if not self._validate_range(val, *ranges[i]):
                        return False

            elif "-" in part:
                # Range
                start, end = part.split("-")
                if not self._validate_range(start, *ranges[i]):
                    return False
                if not self._validate_range(end, *ranges[i]):
                    return False

            else:
                # Single value
                if not self._validate_range(part, *ranges[i]):
                    return False

        return True

    def _validate_range(self, value: str, min_val: int, max_val: int) -> bool:
        """Validate cron value is in range.

        Args:
            value: Value to validate
            min_val: Minimum value
            max_val: Maximum value

        Returns:
            Validation status
        """
        try:
            val = int(value)
            return min_val <= val <= max_val
        except ValueError:
            return False

    def get_newsauto_jobs(self) -> List[Dict[str, str]]:
        """Get all Newsauto cron jobs.

        Returns:
            List of job dictionaries
        """
        jobs = self.list_jobs()
        newsauto_jobs = []

        for job in jobs:
            if self.cron_identifier in job:
                parts = job.split(None, 5)
                if len(parts) >= 6:
                    schedule = " ".join(parts[:5])
                    rest = parts[5]

                    # Extract command and comment
                    if self.cron_identifier in rest:
                        cmd_parts = rest.split(self.cron_identifier)
                        command = cmd_parts[0].strip()
                        comment = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""
                    else:
                        command = rest
                        comment = ""

                    newsauto_jobs.append(
                        {
                            "schedule": schedule,
                            "command": command,
                            "comment": comment,
                            "full_line": job,
                        }
                    )

        return newsauto_jobs


class SystemdManager:
    """Manages systemd services for newsletter automation."""

    def __init__(self, service_name: str = "newsauto"):
        """Initialize systemd manager.

        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self.service_file = f"/etc/systemd/system/{service_name}.service"

    def create_service_file(
        self, exec_path: str, working_dir: str, user: str = "www-data"
    ) -> str:
        """Create systemd service file content.

        Args:
            exec_path: Path to executable
            working_dir: Working directory
            user: User to run service as

        Returns:
            Service file content
        """
        return f"""[Unit]
Description=Newsauto Newsletter Automation Service
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={exec_path}
Restart=always
RestartSec=10

# Environment
Environment="PYTHONUNBUFFERED=1"

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target"""

    def install_service(
        self, exec_path: str, working_dir: str, user: str = "www-data"
    ) -> bool:
        """Install systemd service.

        Args:
            exec_path: Path to executable
            working_dir: Working directory
            user: User to run service as

        Returns:
            Success status
        """
        try:
            # Create service file
            service_content = self.create_service_file(exec_path, working_dir, user)

            # Write service file (requires sudo)
            with open(self.service_file, "w") as f:
                f.write(service_content)

            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"], check=True)

            # Enable service
            subprocess.run(["systemctl", "enable", self.service_name], check=True)

            logger.info(f"Service {self.service_name} installed successfully")
            return True

        except Exception as e:
            logger.error(f"Error installing service: {e}")
            return False

    def start_service(self) -> bool:
        """Start the service.

        Returns:
            Success status
        """
        try:
            subprocess.run(["systemctl", "start", self.service_name], check=True)
            logger.info(f"Service {self.service_name} started")
            return True
        except Exception as e:
            logger.error(f"Error starting service: {e}")
            return False

    def stop_service(self) -> bool:
        """Stop the service.

        Returns:
            Success status
        """
        try:
            subprocess.run(["systemctl", "stop", self.service_name], check=True)
            logger.info(f"Service {self.service_name} stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping service: {e}")
            return False

    def get_service_status(self) -> Optional[str]:
        """Get service status.

        Returns:
            Service status or None
        """
        try:
            result = subprocess.run(
                ["systemctl", "status", self.service_name],
                capture_output=True,
                text=True,
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return None
