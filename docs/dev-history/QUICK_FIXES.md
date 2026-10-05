# Quick Fixes - Priority Actions

## Critical Bugs (Fix Immediately)

### 1. Fix Trailing Space Bug
**File**: `wparc/wpapi/crawler.py`  
**Lines**: 53, 57  
**Change**: `'wp_v2_media.jsonl '` → `'wp_v2_media.jsonl'`

### 2. Add Missing Dependencies
**File**: `setup.py`  
**Add to `install_requires`**:
```python
'requests',
'urllib3',
```

### 3. Fix Incorrect References
**File**: `wparc/__init__.py`  
**Line 2**: Change docstring from "yspcrawler: a command-line tool to backup documents from Yandex.Disk" to "wparc: a command-line tool to backup public data from WordPress websites"

**File**: `wparc/__main__.py`  
**Line 2**: Change comment from "spcrawler" to "wparc"

**File**: `tox.ini`  
**Line 21**: Change `./spcrawler` to `./wparc`

## Security Fixes

### 4. Add SSL Verification Option
**File**: `wparc/wpapi/crawler.py`  
- Add parameter to control SSL verification
- Default to `verify=True` for security
- Document security implications

### 5. Fix Command Injection Risk
**File**: `wparc/wpapi/crawler.py` line 48  
**Replace**: `os.system()` with `subprocess.run()` using proper argument handling

## Code Quality Quick Wins

### 6. Use Context Managers for Files
**File**: `wparc/wpapi/crawler.py`  
Replace all `open()` calls with `with open()` statements

### 7. Fix Bare Except
**File**: `wparc/wpapi/crawler.py` line 149  
Replace `except:` with specific exception handling

### 8. Remove Commented Code
Clean up all commented-out code blocks

### 9. Fix Function Naming
**File**: `wparc/core.py`  
Rename `enableVerbose()` to `enable_verbose()`

### 10. Consolidate CLI Groups
**File**: `wparc/core.py`  
Merge `cli1`, `cli2`, `cli3` into single `cli` group

## Example Fixes

### Example 1: File Handling
```python
# Before
f = open(outfile, 'w', encoding='utf8')
f.write(json.dumps(wpjson, ensure_ascii=False))
f.close()

# After
with open(outfile, 'w', encoding='utf8') as f:
    f.write(json.dumps(wpjson, ensure_ascii=False))
```

### Example 2: Error Handling
```python
# Before
resp = requests.get(url, headers=REQUEST_HEADER, timeout=DEFAULT_TIMEOUT)

# After
try:
    resp = requests.get(url, headers=REQUEST_HEADER, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
except requests.exceptions.RequestException as e:
    logging.error(f"Failed to fetch {url}: {e}")
    raise
```

### Example 3: CLI Consolidation
```python
# Before: Three separate groups
@click.group()
def cli1(): pass

@click.group()
def cli2(): pass

@click.group()
def cli3(): pass

# After: Single group
@click.group()
def cli():
    """WordPress API crawler and backup tool"""
    pass

@cli.command()
@click.option('--domain', '-d', required=True, help='Domain name')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def ping(domain, verbose):
    """Ping WordPress API endpoint"""
    ...
```
