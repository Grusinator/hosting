import subprocess
from invoke import task, Collection

import base64
import os
import platform
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
from invoke import task
from loguru import logger

load_dotenv()


def check_docker_installed():
    """Check if Docker is installed by running `docker --version`."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True, text=True)
        print("Docker is installed and running.")
    except subprocess.CalledProcessError:
        print("Docker is not installed or not running correctly. Please install Docker and ensure it is running.")
        exit(1)


def start_docker():
    """Start Docker daemon if it is not running."""
    system = platform.system()
    if system == "Windows":
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if "error during connect" in result.stderr:
            logger.info("Starting Docker Desktop...")
            docker_desktop_path = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
            if os.path.exists(docker_desktop_path):
                logger.info(f"Found Docker Desktop at {docker_desktop_path}, starting it now...")
                subprocess.Popen([docker_desktop_path], shell=True)
            else:
                logger.error(f"Docker Desktop executable not found at {docker_desktop_path}")
                exit(1)
            # Wait for Docker to start
            max_attempts = 30
            for attempt in range(max_attempts):
                result = subprocess.run(["docker", "info"], capture_output=True, text=True)
                if "error during connect" not in result.stderr:
                    logger.info("Docker Desktop is running.")
                    break
                logger.info(f"Waiting for Docker Desktop to start... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(5)
            else:
                logger.error("Docker Desktop did not start in the expected time.")
                exit(1)
    else:
        result = subprocess.run(["systemctl", "is-active", "--quiet", "docker"])
        if result.returncode != 0:
            logger.info("Starting Docker service...")
            subprocess.run(["sudo", "systemctl", "start", "docker"])



@task
def check_docker(ctx):
    """Check if Docker is installed and running."""
    ctx.run("docker --version")
    ctx.run("docker info")

@task
def start_docker_deamon(ctx):
    """Start Docker daemon if it is not running."""
    check_docker_installed()
    start_docker()
    print("Docker has been started successfully.")
