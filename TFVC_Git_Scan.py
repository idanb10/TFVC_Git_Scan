import requests
import json
import os
import zipfile
import time
import subprocess
import base64
from datetime import datetime
from urllib.parse import urlparse

BASE_URL = "http://localhost/DefaultCollection"
AZURE_PAT = "<your-azure-devops-pat>"
AUTH_TOKEN = base64.b64encode(f":{AZURE_PAT}".encode()).decode()

GITLAB_TOKEN = "your-gitlab-token-here"
OUTPUT_DIR = "tfvc_downloads"
GIT_OUTPUT_DIR = "git_downloads"
API_VERSION = "7.2-preview"

CHECKMARX_BASE_URI = "https://eu-2.ast.checkmarx.net"
CHECKMARX_AUTH_URI = "https://eu-2.iam.checkmarx.net"
CHECKMARX_CLIENT_ID = "<client-id>"
CHECKMARX_CLIENT_SECRET = "<client-secret"
CHECKMARX_TENANT = "<tenant-name>"
CX_CLI_PATH = "ast-cli_2.3.36_windows_x64/cx.exe"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(GIT_OUTPUT_DIR, exist_ok=True)

headers = {
    "Authorization": f"Basic {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_main_menu():
    clear_screen()
    print("="*60)
    print(" DevOps Automation Script")
    print("="*60)
    print("\nPlease select an option:\n")
    print("  1. Download Git repos from git-repos.txt")
    print("  2. Download TFVC repos from Azure DevOps Server")
    print("  3. Scan projects in Checkmarx One using AST-CLI")
    print("  0. Exit")
    print("\n" + "="*60)

def show_tfvc_menu():
    print("\n" + "-"*60)
    print(" TFVC Download Options")
    print("-"*60)
    print("\n  1. Download all TFVC projects")
    print("  2. Download a specific project")
    print("  0. Back to main menu")
    print("\n" + "-"*60)

def get_projects():
    url = f"{BASE_URL}/_apis/projects?api-version={API_VERSION}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['value']

def get_tfvc_items(project_name):
    url = f"{BASE_URL}/{project_name}/_apis/tfvc/items"
    params = {
        "scopePath": f"$/{project_name}",
        "recursionLevel": "Full",
        "api-version": API_VERSION
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['value']

def download_file(project_name, item_path):
    url = f"{BASE_URL}/{project_name}/_apis/tfvc/items"
    params = {
        "path": item_path,
        "api-version": API_VERSION
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.content

def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def download_project_as_zip(project_name):
    print(f"\n{'='*60}")
    print(f"Project: {project_name}")
    print(f"{'='*60}")
    
    try:
        print("Retrieving file list...")
        items = get_tfvc_items(project_name)
    except Exception as e:
        print(f"❌ Error getting items: {e}")
        return False
    
    files = [item for item in items if not item.get('isFolder', False)]
    
    if not files:
        print(f"⚠️  No files found in {project_name}")
        return False
    
    print(f"Found {len(files)} file(s) to download\n")
    
    zip_filename = os.path.join(OUTPUT_DIR, f"{project_name}.zip")
    total_size = 0
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for idx, file_item in enumerate(files, 1):
            file_path = file_item['path']
            
            progress = f"[{idx}/{len(files)}]"
            print(f"{progress} {file_path}")
            
            try:
                content = download_file(project_name, file_path)
                total_size += len(content)
                
                relative_path = file_path.replace(f"$/{project_name}/", "")
                
                zipf.writestr(relative_path, content)
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    zip_size = os.path.getsize(zip_filename)
    
    print(f"\n✅ Successfully created: {zip_filename}")
    print(f"   Total content size: {format_size(total_size)}")
    print(f"   Compressed size: {format_size(zip_size)}")
    print(f"   Compression ratio: {(1 - zip_size/total_size)*100:.1f}%")
    
    return True

def download_all_tfvc_projects():
    start_time = time.time()
    
    print("\n" + "="*60)
    print("Downloading All TFVC Projects")
    print("="*60)
    print(f"Server: {BASE_URL}")
    print(f"Output: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        print("\nFetching project list...")
        projects = get_projects()
        print(f"Found {len(projects)} project(s)")
    except Exception as e:
        print(f"❌ Error getting projects: {e}")
        input("\nPress Enter to continue...")
        return
    
    success_count = 0
    for project in projects:
        if download_project_as_zip(project['name']):
            success_count += 1
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print("DOWNLOAD COMPLETE")
    print(f"{'='*60}")
    print(f"Successfully downloaded: {success_count}/{len(projects)} project(s)")
    print(f"Total time: {elapsed:.2f} seconds")
    print(f"Output location: {os.path.abspath(OUTPUT_DIR)}")
    print(f"{'='*60}")
    
    input("\nPress Enter to continue...")

def download_specific_tfvc_project():
    print("\n" + "="*60)
    print("Download Specific TFVC Project")
    print("="*60)
    
    try:
        print("\nFetching available projects...")
        projects = get_projects()
        
        if not projects:
            print("❌ No projects found")
            input("\nPress Enter to continue...")
            return
        
        print(f"\nAvailable projects:")
        for idx, project in enumerate(projects, 1):
            print(f"  {idx}. {project['name']}")
        
    except Exception as e:
        print(f"❌ Error getting projects: {e}")
        input("\nPress Enter to continue...")
        return
    
    print("\n" + "-"*60)
    project_name = input("Enter project name (or press Enter to cancel): ").strip()
    
    if not project_name:
        print("Cancelled.")
        input("\nPress Enter to continue...")
        return
    
    project_exists = any(p['name'].lower() == project_name.lower() for p in projects)
    
    if not project_exists:
        print(f"\n⚠️  Warning: Project '{project_name}' not found in the list.")
        confirm = input("Do you want to try downloading it anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            input("\nPress Enter to continue...")
            return
    
    start_time = time.time()
    success = download_project_as_zip(project_name)
    elapsed = time.time() - start_time
    
    if success:
        print(f"\n✅ Download completed in {elapsed:.2f} seconds")
    else:
        print(f"\n❌ Download failed")
    
    input("\nPress Enter to continue...")

def handle_tfvc_option():
    while True:
        clear_screen()
        print("="*60)
        print(" DevOps Automation Script")
        print("="*60)
        show_tfvc_menu()
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "1":
            download_all_tfvc_projects()
        elif choice == "2":
            download_specific_tfvc_project()
        elif choice == "0":
            break
        else:
            print("\n❌ Invalid option. Please try again.")
            time.sleep(1)

def parse_git_url(url):
    url = url.strip()
    
    url = url.rstrip('/')
    
    parsed = urlparse(url)
    
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path
    
    if '/-/' in path:
        path = path.split('/-/')[0]
    
    if not path.endswith('.git'):
        path = path + '.git'
    
    clone_url = f"{base_url}{path}"
    
    project_name = path.split('/')[-1].replace('.git', '')
    
    return clone_url, project_name, base_url

def clone_git_repo(repo_url, project_name, base_url):
    print(f"\n{'='*60}")
    print(f"Repository: {project_name}")
    print(f"{'='*60}")
    print(f"URL: {repo_url}")
    
    if GITLAB_TOKEN and GITLAB_TOKEN != "your-gitlab-token-here":
        parsed = urlparse(repo_url)
        auth_url = f"{parsed.scheme}://oauth2:{GITLAB_TOKEN}@{parsed.netloc}{parsed.path}"
    else:
        auth_url = repo_url
        print("⚠️  Warning: No GitLab token configured. Attempting without authentication...")
    
    target_dir = os.path.join(GIT_OUTPUT_DIR, project_name)
    
    if os.path.exists(target_dir):
        print(f"⚠️  Directory already exists: {target_dir}")
        print("Skipping clone...")
        return False
    
    print("\nCloning repository (trying 'main' branch)...")
    result = subprocess.run(
        ['git', 'clone', '--branch', 'main', '--single-branch', auth_url, target_dir],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("'main' branch not found, trying 'master' branch...")
        result = subprocess.run(
            ['git', 'clone', '--branch', 'master', '--single-branch', auth_url, target_dir],
            capture_output=True,
            text=True
        )
    
    if result.returncode == 0:
        print(f"✅ Successfully cloned to: {target_dir}")
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(target_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        
        print(f"   Repository size: {format_size(total_size)}")
        return True
    else:
        print(f"❌ Failed to clone repository")
        print(f"Error: {result.stderr}")
        return False

def read_git_repos_file():
    repos_file = "git-repos.txt"
    
    if not os.path.exists(repos_file):
        print(f"❌ File not found: {repos_file}")
        print(f"\nPlease create '{repos_file}' in the same directory as this script.")
        print("Add one GitLab URL per line (copied from your browser address bar).")
        print("\nExample:")
        print("  https://gitlab.company.com/team/project1")
        print("  https://gitlab.company.com/team/project2")
        return None
    
    with open(repos_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    if not lines:
        print(f"❌ No URLs found in {repos_file}")
        print("Please add at least one GitLab URL.")
        return None
    
    return lines

def handle_git_option():
    start_time = time.time()
    
    print("\n" + "="*60)
    print("Download Git Repos from git-repos.txt")
    print("="*60)
    print(f"Output: {os.path.abspath(GIT_OUTPUT_DIR)}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\nChecking for Git installation...")
    result = subprocess.run(['git', '--version'], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Git is not installed or not in PATH")
        print("Please install Git and try again.")
        input("\nPress Enter to continue...")
        return
    
    print(f"✅ {result.stdout.strip()}")
    
    print("\nReading git-repos.txt...")
    urls = read_git_repos_file()
    
    if not urls:
        input("\nPress Enter to continue...")
        return
    
    print(f"Found {len(urls)} repository URL(s)")
    
    success_count = 0
    failed_repos = []
    
    for url in urls:
        try:
            clone_url, project_name, base_url = parse_git_url(url)
            if clone_git_repo(clone_url, project_name, base_url):
                success_count += 1
            else:
                failed_repos.append(project_name)
        except Exception as e:
            print(f"\n❌ Error processing URL '{url}': {e}")
            failed_repos.append(url)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print("CLONE COMPLETE")
    print(f"{'='*60}")
    print(f"Successfully cloned: {success_count}/{len(urls)} repository(ies)")
    if failed_repos:
        print(f"\nFailed repositories:")
        for repo in failed_repos:
            print(f"  - {repo}")
    print(f"\nTotal time: {elapsed:.2f} seconds")
    print(f"Output location: {os.path.abspath(GIT_OUTPUT_DIR)}")
    print(f"{'='*60}")
    
    input("\nPress Enter to continue...")

def get_git_branch(repo_path):
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    return 'main'

def scan_with_checkmarx(source_path, project_name, source_type="folder", branch="main"):
    print(f"\n{'='*60}")
    print(f"Scanning: {project_name}")
    print(f"{'='*60}")
    print(f"Source: {source_path}")
    print(f"Type: {source_type}")
    print(f"Branch: {branch}")
    
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
    
    print("\nInitiating scan...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("✅ Scan initiated successfully!")
            if result.stdout:
                print("\nScan details:")
                print(result.stdout)
            return True
        else:
            print(f"❌ Scan failed with exit code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Scan timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running scan: {e}")
        return False

def validate_checkmarx_auth():
    print("Validating Checkmarx authentication...")
    
    cmd = [
        CX_CLI_PATH,
        "auth", "validate",
        "--base-uri", CHECKMARX_BASE_URI,
        "--base-auth-uri", CHECKMARX_AUTH_URI,
        "--client-id", CHECKMARX_CLIENT_ID,
        "--client-secret", CHECKMARX_CLIENT_SECRET
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Authentication successful!")
            return True
        else:
            print("❌ Authentication failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error validating authentication: {e}")
        return False

def handle_checkmarx_option():
    start_time = time.time()
    
    print("\n" + "="*60)
    print("Scan Projects in Checkmarx One")
    print("="*60)
    print(f"Checkmarx URL: {CHECKMARX_BASE_URI}")
    print(f"Tenant: {CHECKMARX_TENANT}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if CHECKMARX_CLIENT_ID == "your-client-id-here" or CHECKMARX_CLIENT_SECRET == "your-client-secret-here":
        print("\n❌ Checkmarx credentials not configured!")
        print("Please update the script with your OAuth Client ID and Secret.")
        input("\nPress Enter to continue...")
        return
    
    if not os.path.exists(CX_CLI_PATH):
        print(f"\n❌ Checkmarx CLI not found at: {CX_CLI_PATH}")
        print("Please update CX_CLI_PATH in the script configuration.")
        input("\nPress Enter to continue...")
        return
    
    print(f"\n✅ Found Checkmarx CLI: {CX_CLI_PATH}")
    
    if not validate_checkmarx_auth():
        print("\n❌ Cannot proceed without valid authentication.")
        input("\nPress Enter to continue...")
        return
    
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
    
    if os.path.exists(OUTPUT_DIR):
        tfvc_zips = [f for f in os.listdir(OUTPUT_DIR) 
                     if f.endswith('.zip')]
        for zip_file in tfvc_zips:
            project_name = zip_file.replace('.zip', '')
            sources_to_scan.append({
                'path': os.path.abspath(os.path.join(OUTPUT_DIR, zip_file)),
                'name': project_name,
                'type': 'zip',
                'branch': 'main'
            })
    
    if not sources_to_scan:
        print("\n⚠️  No sources found to scan!")
        print(f"Please ensure you have downloaded repos in:")
        print(f"  - {GIT_OUTPUT_DIR}/")
        print(f"  - {OUTPUT_DIR}/")
        input("\nPress Enter to continue...")
        return
    
    print(f"\n{'='*60}")
    print(f"Found {len(sources_to_scan)} project(s) to scan:")
    print(f"{'='*60}")
    for idx, source in enumerate(sources_to_scan, 1):
        print(f"  {idx}. {source['name']} ({source['type']}, branch: {source['branch']})")
    
    print(f"\n{'='*60}")
    confirm = input("Proceed with scanning all projects? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Cancelled.")
        input("\nPress Enter to continue...")
        return
    
    success_count = 0
    failed_scans = []
    
    for idx, source in enumerate(sources_to_scan, 1):
        print(f"\n{'='*60}")
        print(f"Progress: {idx}/{len(sources_to_scan)}")
        print(f"{'='*60}")
        
        if scan_with_checkmarx(source['path'], source['name'], source['type'], source['branch']):
            success_count += 1
        else:
            failed_scans.append(source['name'])
        
        if idx < len(sources_to_scan):
            time.sleep(2)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print("SCANNING COMPLETE")
    print(f"{'='*60}")
    print(f"Successfully scanned: {success_count}/{len(sources_to_scan)} project(s)")
    
    if failed_scans:
        print(f"\nFailed scans:")
        for scan in failed_scans:
            print(f"  - {scan}")
    
    print(f"\nTotal time: {elapsed:.2f} seconds")
    print(f"View results at: {CHECKMARX_BASE_URI}")
    print(f"{'='*60}")
    
    input("\nPress Enter to continue...")

def main():
    while True:
        show_main_menu()
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "1":
            handle_git_option()
        elif choice == "2":
            handle_tfvc_option()
        elif choice == "3":
            handle_checkmarx_option()
        elif choice == "0":
            print("\nExiting... Goodbye!")
            break
        else:
            print("\n❌ Invalid option. Please try again.")
            time.sleep(1)

if __name__ == "__main__":

    main()
