# DevOps Automation Script

A Python script for downloading repositories from Azure DevOps Server (TFVC) and GitLab, and scanning them with Checkmarx One.

## Requirements

### System Requirements

1. **Python 3.7+**
   - Download from [python.org](https://www.python.org/downloads/)

2. **Git** (for cloning Git repositories)
   - Download from [git-scm.com](https://git-scm.com/downloads)
   - Must be accessible from command line (`git --version` should work)

3. **Checkmarx AST CLI 2.3.36** (for security scanning)
   - Download from [Checkmarx GitHub](https://github.com/Checkmarx/ast-cli/releases/tag/2.3.36)
   - Extract and note the path to `cx.exe`

### Python Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

Required packages:
- `requests>=2.30.0`

## Configuration

Before running the script, update these configuration variables in the Python file:

### Azure DevOps Server (TFVC)
```python
BASE_URL = "http://localhost/DefaultCollection"  # Your Azure DevOps Server URL
AUTH_TOKEN = "your-base64-encoded-token"         # Base64 encoded credentials
```

### GitLab
```python
GITLAB_TOKEN = "your-gitlab-token-here"  # GitLab Personal Access Token
```

To get a GitLab token:
1. Go to GitLab → Settings → Access Tokens
2. Create a token with `read_repository` scope

### Checkmarx One
```python
CHECKMARX_BASE_URI = "https://eu.ast.checkmarx.net"     # Your region's base URL
CHECKMARX_AUTH_URI = "https://eu.iam.checkmarx.net"     # Your region's IAM URL
CHECKMARX_CLIENT_ID = "your-client-id"                  # OAuth Client ID
CHECKMARX_CLIENT_SECRET = "your-client-secret"          # OAuth Client Secret
CHECKMARX_TENANT = "your-tenant-name"                   # Your tenant name
CX_CLI_PATH = "path/to/cx.exe"                          # Path to Checkmarx CLI
```

## Setup

1. **Clone or download this repository**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Git** (if not already installed)

4. **Download Checkmarx AST CLI** (if using scanning feature)

5. **Update configuration** in the script with your credentials

6. **Create git-repos.txt** (for Git repository downloads)
   - Create a file named `git-repos.txt` in the same directory
   - Add one GitLab URL per line:
   ```
   https://gitlab.company.com/team/project1
   https://gitlab.company.com/team/project2
   ```

## Usage

Run the script:

```bash
python script_name.py
```

The script provides three main options:

1. **Download Git repos** - Clones repositories listed in `git-repos.txt`
2. **Download TFVC repos** - Downloads projects from Azure DevOps Server
3. **Scan with Checkmarx** - Scans downloaded repositories for security issues

## Output Directories

- `git_downloads/` - Cloned Git repositories
- `tfvc_downloads/` - TFVC projects as ZIP files

## Troubleshooting

**"Git is not installed or not in PATH"**
- Install Git and ensure it's accessible from command line

**"Checkmarx CLI not found"**
- Update `CX_CLI_PATH` with the correct path to `cx.exe`

**"Authentication failed"**
- Verify your tokens and credentials are correct
- Check that tokens haven't expired

**"No files found in project"**
- Ensure the Azure DevOps project contains files
- Verify your authentication token has proper permissions