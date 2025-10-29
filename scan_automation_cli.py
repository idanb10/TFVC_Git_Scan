import requests
import json
import os
import zipfile
import time
import subprocess
import base64
import argparse
import shutil
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from urllib.parse import urlparse

# TFS Configuration
BASE_URL = "http://localhost/DefaultCollection"
AZURE_PAT = "azure-pat"
AUTH_TOKEN = base64.b64encode(f":{AZURE_PAT}".encode()).decode()
OUTPUT_DIR = "tfvc_downloads"
API_VERSION = "7.2-preview"

# GitLab Configuration
GITLAB_TOKEN = "gitlab-token"
GIT_OUTPUT_DIR = "git_downloads"

# Checkmarx Configuration
CHECKMARX_BASE_URI = "https://eu-2.ast.checkmarx.net"
CHECKMARX_AUTH_URI = "https://eu-2.iam.checkmarx.net"
CHECKMARX_CLIENT_ID = "client-id"
CHECKMARX_CLIENT_SECRET = "client-secret"
CHECKMARX_TENANT = "my-tenant"
CX_CLI_PATH = "ast-cli_2.3.36_windows_x64/cx.exe"

# Proxy
# Format: "http://proxy-server:port" or "http://username:password@proxy-server:port"
PROXY_URL = ""

LOG_DIR = "logs"
LOG_FILE = "devops_automation.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(GIT_OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

headers = {
    "Authorization": f"Basic {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def setup_logging(log_level=logging.INFO):
    """
    Configure logging with both file and console handlers.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = logging.getLogger('DevOpsAutomation')
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        logger.handlers.clear()
    
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - [%(levelname)s] - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        fmt='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    log_file_path = os.path.join(LOG_DIR, LOG_FILE)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

def format_size(size_bytes):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_projects():
    """Get all projects in the collection"""
    url = f"{BASE_URL}/_apis/projects?api-version={API_VERSION}"
    logger.debug(f"Fetching projects from: {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['value']

def get_tfvc_items(project_name):
    """Get all TFVC items recursively for a project"""
    url = f"{BASE_URL}/{project_name}/_apis/tfvc/items"
    params = {
        "scopePath": f"$/{project_name}",
        "recursionLevel": "Full",
        "api-version": API_VERSION
    }
    logger.debug(f"Fetching TFVC items for project: {project_name}")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['value']

def download_file(project_name, item_path):
    """Download a single file from TFVC"""
    url = f"{BASE_URL}/{project_name}/_apis/tfvc/items"
    params = {
        "path": item_path,
        "api-version": API_VERSION
    }
    logger.debug(f"Downloading file: {item_path}")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.content

def download_project_as_zip(project_name):
    """Download entire project and create a zip file"""
    logger.info(f"Starting download: {project_name}")
    
    try:
        logger.info(f"Retrieving file list for {project_name}...")
        items = get_tfvc_items(project_name)
    except Exception as e:
        logger.error(f"Error getting items for {project_name}: {e}", exc_info=True)
        return False
    
    files = [item for item in items if not item.get('isFolder', False)]
    
    if not files:
        logger.warning(f"No files found in {project_name}")
        return False
    
    logger.info(f"Found {len(files)} file(s) in {project_name}")
    
    zip_filename = os.path.join(OUTPUT_DIR, f"{project_name}.zip")
    total_size = 0
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for idx, file_item in enumerate(files, 1):
            file_path = file_item['path']
            
            if idx % 10 == 0 or idx == len(files):
                logger.info(f"Progress: {idx}/{len(files)} files")
            
            try:
                content = download_file(project_name, file_path)
                total_size += len(content)
                relative_path = file_path.replace(f"$/{project_name}/", "")
                zipf.writestr(relative_path, content)
            except Exception as e:
                logger.error(f"Error downloading {file_path}: {e}")
    
    zip_size = os.path.getsize(zip_filename)
    logger.info(f"Created: {zip_filename} - Size: {format_size(zip_size)}")
    
    return True

def download_all_tfvc_projects():
    """Download all TFVC projects"""
    logger.info("Starting TFVC download for all projects")
    start_time = time.time()
    
    try:
        projects = get_projects()
        logger.info(f"Found {len(projects)} TFVC project(s)")
    except Exception as e:
        logger.error(f"Error getting projects: {e}", exc_info=True)
        return False
    
    success_count = 0
    for project in projects:
        if download_project_as_zip(project['name']):
            success_count += 1
    
    elapsed = time.time() - start_time
    logger.info(f"TFVC download complete: {success_count}/{len(projects)} projects in {elapsed:.2f}s")
    
    return success_count > 0

def download_specific_tfvc_project(project_name):
    """Download a specific TFVC project"""
    logger.info(f"Starting TFVC download for project: {project_name}")
    start_time = time.time()
    
    success = download_project_as_zip(project_name)
    elapsed = time.time() - start_time
    
    if success:
        logger.info(f"Download completed in {elapsed:.2f} seconds")
    else:
        logger.error(f"Download failed")
    
    return success

def parse_git_url(url):
    """Parse GitLab URL from browser address bar and convert to clone URL"""
    url = url.strip().rstrip('/')
    parsed = urlparse(url)
    
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path
    
    if '/-/' in path:
        path = path.split('/-/')[0]
    
    if not path.endswith('.git'):
        path = path + '.git'
    
    clone_url = f"{base_url}{path}"
    project_name = path.split('/')[-1].replace('.git', '')
    
    logger.debug(f"Parsed URL - Original: {url}, Clone: {clone_url}, Project: {project_name}")
    
    return clone_url, project_name, base_url

def clone_git_repo(repo_url, project_name):
    """Clone a Git repository using git clone command"""
    logger.info(f"Cloning repository: {project_name}")
    
    if GITLAB_TOKEN and GITLAB_TOKEN != "your-gitlab-token-here":
        parsed = urlparse(repo_url)
        auth_url = f"{parsed.scheme}://oauth2:{GITLAB_TOKEN}@{parsed.netloc}{parsed.path}"
    else:
        auth_url = repo_url
        logger.warning("No GitLab token configured, attempting without authentication")
    
    target_dir = os.path.join(GIT_OUTPUT_DIR, project_name)
    
    if os.path.exists(target_dir):
        logger.warning(f"Directory already exists, skipping: {target_dir}")
        return False
    
    logger.debug(f"Attempting to clone branch 'main' for {project_name}")
    result = subprocess.run(
        ['git', 'clone', '--branch', 'main', '--single-branch', auth_url, target_dir],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.debug(f"Branch 'main' not found, trying 'master' for {project_name}")
        result = subprocess.run(
            ['git', 'clone', '--branch', 'master', '--single-branch', auth_url, target_dir],
            capture_output=True,
            text=True
        )
    
    if result.returncode == 0:
        total_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(target_dir)
            for filename in filenames
        )
        logger.info(f"Successfully cloned: {project_name} - Size: {format_size(total_size)}")
        return True
    else:
        logger.error(f"Failed to clone {project_name}: {result.stderr}")
        return False

def read_git_repos_file(repos_file="git-repos.txt"):
    """Read git-repos.txt and return list of URLs"""
    if not os.path.exists(repos_file):
        logger.error(f"File not found: {repos_file}")
        return None
    
    with open(repos_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    if not lines:
        logger.error(f"No URLs found in {repos_file}")
        return None
    
    logger.debug(f"Read {len(lines)} URLs from {repos_file}")
    return lines

def download_all_git_repos(repos_file="git-repos.txt"):
    """Download all Git repos from file"""
    logger.info("Starting Git repos download")
    start_time = time.time()
    
    result = subprocess.run(['git', '--version'], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Git is not installed or not in PATH")
        return False
    
    logger.info(f"Git version: {result.stdout.strip()}")
    
    urls = read_git_repos_file(repos_file)
    if not urls:
        return False
    
    logger.info(f"Found {len(urls)} repository URL(s)")
    
    success_count = 0
    for url in urls:
        try:
            clone_url, project_name, base_url = parse_git_url(url)
            if clone_git_repo(clone_url, project_name):
                success_count += 1
        except Exception as e:
            logger.error(f"Error processing URL '{url}': {e}", exc_info=True)
    
    elapsed = time.time() - start_time
    logger.info(f"Git clone complete: {success_count}/{len(urls)} repos in {elapsed:.2f}s")
    
    return success_count > 0

def get_git_branch(repo_path):
    """Get the current branch name from a Git repository"""
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            logger.debug(f"Git branch for {repo_path}: {branch}")
            return branch
    except Exception as e:
        logger.debug(f"Could not determine branch for {repo_path}: {e}")
    return 'main'

def validate_checkmarx_auth():
    """Validate Checkmarx authentication"""
    logger.info("Validating Checkmarx authentication...")
    
    cmd = [
        CX_CLI_PATH,
        "auth", "validate",
        "--base-uri", CHECKMARX_BASE_URI,
        "--base-auth-uri", CHECKMARX_AUTH_URI,
        "--client-id", CHECKMARX_CLIENT_ID,
        "--client-secret", CHECKMARX_CLIENT_SECRET
    ]
    
    if PROXY_URL:
        cmd.extend(["--proxy", PROXY_URL])
        logger.debug(f"Using proxy: {PROXY_URL}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("Authentication successful")
            return True
        else:
            logger.error(f"Authentication failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error validating authentication: {e}", exc_info=True)
        return False

def scan_with_checkmarx(source_path, project_name, source_type="folder", branch="main"):
    """Scan a project using Checkmarx One CLI"""
    logger.info(f"Scanning: {project_name} (type: {source_type}, branch: {branch})")
    
    cmd = [
        CX_CLI_PATH,
        "scan", "create", "--async",
        "--project-name", project_name,
        "-s", source_path,
        "--branch", branch,
        "--base-uri", CHECKMARX_BASE_URI,
        "--base-auth-uri", CHECKMARX_AUTH_URI,
        "--client-id", CHECKMARX_CLIENT_ID,
        "--client-secret", CHECKMARX_CLIENT_SECRET,
        "--tenant", CHECKMARX_TENANT
    ]

    if PROXY_URL:
        cmd.extend(["--proxy", PROXY_URL])
    
    logger.debug(f"Checkmarx scan command: {' '.join([c if 'secret' not in c.lower() else '***' for c in cmd])}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"Scan initiated successfully: {project_name}")
            if result.stdout:
                logger.debug(f"Scan output: {result.stdout}")
            return True
        else:
            logger.error(f"Scan failed for {project_name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Scan timed out: {project_name}")
        return False
    except Exception as e:
        logger.error(f"Error running scan for {project_name}: {e}", exc_info=True)
        return False

def scan_all_projects():
    """Scan all downloaded projects in Checkmarx"""
    logger.info("Starting Checkmarx scans")
    start_time = time.time()
    
    if CHECKMARX_CLIENT_ID == "your-client-id-here" or CHECKMARX_CLIENT_SECRET == "your-client-secret-here":
        logger.error("Checkmarx credentials not configured")
        return False
    
    if not os.path.exists(CX_CLI_PATH):
        logger.error(f"Checkmarx CLI not found at: {CX_CLI_PATH}")
        return False
    
    if not validate_checkmarx_auth():
        logger.error("Cannot proceed without valid authentication")
        return False
    
    sources_to_scan = []
    
    if os.path.exists(GIT_OUTPUT_DIR):
        git_repos = [d for d in os.listdir(GIT_OUTPUT_DIR) 
                     if os.path.isdir(os.path.join(GIT_OUTPUT_DIR, d))]
        for repo in git_repos:
            repo_path = os.path.abspath(os.path.join(GIT_OUTPUT_DIR, repo))
            branch = get_git_branch(repo_path)
            sources_to_scan.append({
                'path': repo_path,
                'name': repo,
                'type': 'folder',
                'branch': branch
            })
        logger.debug(f"Found {len(git_repos)} Git repositories to scan")
    
    if os.path.exists(OUTPUT_DIR):
        tfvc_zips = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.zip')]
        for zip_file in tfvc_zips:
            project_name = zip_file.replace('.zip', '')
            sources_to_scan.append({
                'path': os.path.abspath(os.path.join(OUTPUT_DIR, zip_file)),
                'name': project_name,
                'type': 'zip',
                'branch': 'main'
            })
        logger.debug(f"Found {len(tfvc_zips)} TFVC zip files to scan")
    
    if not sources_to_scan:
        logger.warning("No sources found to scan")
        return False
    
    logger.info(f"Found {len(sources_to_scan)} project(s) to scan")
    
    success_count = 0
    for idx, source in enumerate(sources_to_scan, 1):
        logger.info(f"Progress: {idx}/{len(sources_to_scan)}")
        if scan_with_checkmarx(source['path'], source['name'], source['type'], source['branch']):
            success_count += 1
        
        if idx < len(sources_to_scan):
            time.sleep(2)
    
    elapsed = time.time() - start_time
    logger.info(f"Scanning complete: {success_count}/{len(sources_to_scan)} projects in {elapsed:.2f}s")
    
    return success_count > 0

def remove_readonly(func, path, excinfo):
    """Error handler for shutil.rmtree to handle read-only files"""
    import stat

    os.chmod(path, stat.S_IWRITE)
    func(path)

def cleanup_downloads():
    """Remove downloaded files after scanning"""
    logger.info("Starting cleanup...")
    
    cleaned = []
    errors = []
    
    if os.path.exists(GIT_OUTPUT_DIR):
        try:
            logger.info(f"Removing Git repositories from {GIT_OUTPUT_DIR}...")
            shutil.rmtree(GIT_OUTPUT_DIR, onerror=remove_readonly)
            logger.info(f"Removed: {GIT_OUTPUT_DIR}")
            cleaned.append(GIT_OUTPUT_DIR)
        except Exception as e:
            logger.error(f"Error removing {GIT_OUTPUT_DIR}: {e}", exc_info=True)
            errors.append(f"{GIT_OUTPUT_DIR}: {e}")
    
    if os.path.exists(OUTPUT_DIR):
        try:
            logger.info(f"Removing TFVC downloads from {OUTPUT_DIR}...")
            shutil.rmtree(OUTPUT_DIR, onerror=remove_readonly)
            logger.info(f"Removed: {OUTPUT_DIR}")
            cleaned.append(OUTPUT_DIR)
        except Exception as e:
            logger.error(f"Error removing {OUTPUT_DIR}: {e}", exc_info=True)
            errors.append(f"{OUTPUT_DIR}: {e}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(GIT_OUTPUT_DIR, exist_ok=True)
    
    if errors:
        logger.warning(f"Cleanup completed with {len(errors)} error(s)")
        for error in errors:
            logger.warning(f"  - {error}")
    else:
        logger.info(f"Cleanup complete: removed {len(cleaned)} directory(ies)")
    
    return len(errors) == 0

def main():
    parser = argparse.ArgumentParser(
        description='DevOps Automation CLI - Download and scan repos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all TFVC projects
  %(prog)s --tfvc-all
  
  # Download specific TFVC project
  %(prog)s --tfvc-project "MyProject"
  
  # Download all Git repos from git-repos.txt
  %(prog)s --git-all
  
  # Scan all downloaded projects in Checkmarx
  %(prog)s --scan
  
  # Download all repos and scan them
  %(prog)s --tfvc-all --git-all --scan
  
  # Full workflow with cleanup
  %(prog)s --tfvc-all --git-all --scan --cleanup
  
  # Enable debug logging
  %(prog)s --tfvc-all --log-level DEBUG
        """
    )
    
    parser.add_argument('--tfvc-all', action='store_true',
                        help='Download all TFVC projects')
    parser.add_argument('--tfvc-project', metavar='NAME',
                        help='Download specific TFVC project by name')
    
    parser.add_argument('--git-all', action='store_true',
                        help='Download all Git repos from git-repos.txt')
    parser.add_argument('--git-repos-file', metavar='FILE', default='git-repos.txt',
                        help='Path to file containing Git repo URLs (default: git-repos.txt)')
    
    parser.add_argument('--scan', action='store_true',
                        help='Scan all downloaded projects in Checkmarx')
    
    parser.add_argument('--cleanup', action='store_true',
                        help='Remove downloaded files after completion')
    
    parser.add_argument('--log-level', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO',
                        help='Set the logging level (default: INFO)')
    
    parser.add_argument('--log-file', metavar='FILE',
                        default=os.path.join(LOG_DIR, LOG_FILE),
                        help=f'Path to log file (default: {os.path.join(LOG_DIR, LOG_FILE)})')
    
    args = parser.parse_args()
    
    global logger
    log_level = getattr(logging, args.log_level)
    logger = setup_logging(log_level)
    
    if not any([args.tfvc_all, args.tfvc_project, args.git_all, args.scan, args.cleanup]):
        parser.print_help()
        sys.exit(1)
    
    logger.info("="*60)
    logger.info("DevOps Automation CLI - Starting")
    logger.info(f"Log Level: {args.log_level}")
    logger.info(f"Log File: {args.log_file}")
    logger.info("="*60)
    
    overall_success = True
    
    if args.tfvc_all:
        if not download_all_tfvc_projects():
            overall_success = False
    
    if args.tfvc_project:
        if not download_specific_tfvc_project(args.tfvc_project):
            overall_success = False
    
    if args.git_all:
        if not download_all_git_repos(args.git_repos_file):
            overall_success = False
    
    if args.scan:
        if not scan_all_projects():
            overall_success = False
    
    if args.cleanup:
        cleanup_downloads()
    
    logger.info("="*60)
    if overall_success:
        logger.info("All operations completed successfully")
        logger.info("="*60)
        sys.exit(0)
    else:
        logger.warning("Some operations failed - check logs above")
        logger.info("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()