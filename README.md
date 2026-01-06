# Fuzzy File Organizer

A Python utility that intelligently groups and organizes files with similar names using fuzzy string matching. Perfect for decluttering directories containing files with slightly different naming conventions.

## Note

This project was entirely built by AI, Vibe coded on a whim casually. I was talking with Claude about how to organize a downloads directory and it just spit out some python code and I figured "hey, could put that into a project." So here it is.

## Features

- **Fuzzy Matching**: Groups files by name similarity rather than exact matches
- **Unicode Support**: Full support for Japanese, emojis, and all Unicode characters
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Windows Optimized**: 
  - Handles UNC paths and long paths (260+ characters)
  - Respects reserved filenames (CON, PRN, AUX, etc.)
  - Proper console UTF-8 encoding
- **Safe Workflow**: Always shows a preview before making changes
- **Smart Naming**: Auto-generates folder names based on the most representative filename in each group
- **Conflict Handling**: Automatically handles filename collisions with numbering

## Requirements

- Python 3.6+
- No external dependencies (uses only Python standard library)

## Installation

1. Clone or download the repository
2. No additional packages needed - just run the script

```bash
python file_organizer.py
```

## Testing

A comprehensive test suite is included to verify all functionality. The suite includes 76 tests covering unit tests, integration tests, and edge cases.

### Setup

Install pytest (one-time setup):

```bash
pip install pytest
```

### Running Tests

Run all tests:

```bash
pytest tests/ -v
```

Run tests from a specific category:

```bash
# Unit tests for similarity matching
pytest tests/test_file_organizer.py::TestSimilarityRatio -v

# Unit tests for file clustering
pytest tests/test_file_organizer.py::TestClusterFiles -v

# Unit tests for folder name sanitization
pytest tests/test_file_organizer.py::TestSanitizeFolderName -v

# Integration tests for file organization
pytest tests/test_file_organizer.py::TestOrganizeFiles -v

# Edge case tests
pytest tests/test_file_organizer.py::TestEdgeCases -v
```

Run a specific test:

```bash
pytest tests/test_file_organizer.py::TestSimilarityRatio::test_identical_strings -v
```

### Test Coverage

The test suite covers:

- **Similarity Ratio** (8 tests): String comparison logic, case-insensitivity, unicode handling
- **Clustering** (11 tests): File grouping, threshold validation, edge cases
- **Representative Naming** (7 tests): Folder name generation from file lists
- **Sanitization** (12 tests): Invalid character handling, Windows reserved names, path limits
- **File Exclusion** (6 tests): System file filtering
- **File Organization** (12 tests): Dry-run mode, actual movement, collision handling, error scenarios
- **Input Validation** (10 tests): Threshold and directory validation
- **Edge Cases** (5 tests): Unicode files, long names, multiple extensions
- **Helper Functions** (5 tests): Test utility validation

### Test Data

Pre-generated sample files are located in `tests/fixtures/sample_files/`:

- **Photos**: `photo_v1.jpg`, `photo_v2.jpg`, `photo_final.jpg`
- **Documents**: `report_draft.pdf`, `report_final.pdf`, `summary.pdf`
- **Text files**: `file_test_1.txt`, `file_test_2.txt`, `file_test_3.txt`, `readme_v1/v2/final.txt`
- **Archives**: `data_backup_2024.zip`, `data_backup_2025.zip`
- **Isolated**: `isolated_file.doc`

These files are used to test the clustering and organization features with realistic file names.

### Test Configuration

Tests use pytest fixtures and temporary directories to safely validate functionality without affecting your actual files. User input is automatically mocked during integration tests.

## Usage

### Interactive Mode

Run the script without arguments to use interactive mode:

```bash
python file_organizer.py
```

You'll be prompted to:
1. Enter the directory path to organize
2. Set the similarity threshold (0.5 - 0.95)
3. Review the preview of groups
4. Confirm before organizing

### Command-Line Mode

Provide the directory as an argument:

```bash
python file_organizer.py "C:\Downloads"
```

You'll still be prompted for the threshold and confirmation.

## Similarity Threshold

The threshold controls how similar filenames need to be to group together:

- **0.95** - Very strict (only near-identical files group together)
- **0.7** - Default (good balance)
- **0.5** - Very loose (groups many variations together)

**Examples with different thresholds:**

Files: `report_v1.pdf`, `report_v2.pdf`, `report_final.pdf`, `summary.pdf`

- Threshold 0.95: Creates no groups (too strict)
- Threshold 0.7: Groups `report_v1.pdf`, `report_v2.pdf`, `report_final.pdf` together
- Threshold 0.5: Might group all four files together

## How It Works

1. **Scan**: Finds all files in the specified directory
2. **Analyze**: Compares each file's name with others using fuzzy matching
3. **Cluster**: Groups similar files together based on your threshold
4. **Preview**: Shows which files will go into which folders
5. **Confirm**: Asks for confirmation before making changes
6. **Organize**: Creates folders and moves files accordingly

## Examples

### Example 1: Invoice Organization

**Before:**
```
Invoice_2024_Jan_10.pdf
Invoice_2024_Jan_15.pdf
Invoice_2024_Jan_20.pdf
Summary.txt
```

**After:**
```
Invoice_2024_Jan/
  ├── Invoice_2024_Jan_10.pdf
  ├── Invoice_2024_Jan_15.pdf
  └── Invoice_2024_Jan_20.pdf
Summary.txt
```

### Example 2: Screenshot Organization (Unicode)

**Before:**
```
スクリーンショット_2024-01-01.png
スクリーンショット_2024-01-02.png
プレビュー_画像.jpg
```

**After:**
```
スクリーンショット_2024/
  ├── スクリーンショット_2024-01-01.png
  └── スクリーンショット_2024-01-02.png
プレビュー_画像.jpg
```

### Example 3: Photo Burst

**Before:**
```
photo_burst_001.jpg
photo_burst_002.jpg
photo_burst_003.jpg
photo_burst_004.jpg
```

**After:**
```
photo_burst/
  ├── photo_burst_001.jpg
  ├── photo_burst_002.jpg
  ├── photo_burst_003.jpg
  └── photo_burst_004.jpg
```

## Windows-Specific Features

The script includes special handling for Windows:

- **UNC Paths**: Supports `\\server\share\path` syntax
- **Drive Letters**: Supports `C:\`, `D:\`, etc.
- **Forward Slashes**: Automatically converts `/` to `\`
- **Reserved Names**: Automatically prefixes Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
- **UTF-8 Console**: Enables proper Unicode display in Windows Command Prompt and PowerShell
- **Long Paths**: Can handle paths longer than Windows' traditional 260-character limit

## File Exclusions

By default, the script excludes system files to prevent accidental organization:

- `.exe` - Executables
- `.dll` - Libraries
- `.sys` - System files
- `.tmp` - Temporary files
- `.lnk` - Windows shortcuts

These files are ignored and won't be organized.

## Safety Features

- **Preview First**: Always shows what will happen before proceeding
- **Confirmation**: Requires explicit user confirmation before moving files
- **Error Handling**: Reports failures without stopping the entire operation
- **Collision Detection**: Automatically renames files if the destination exists
- **Permission Checking**: Verifies write access before starting

## Troubleshooting

### "No similar file groups found"

Try lowering the similarity threshold. Your files might not be similar enough with the current setting.

### Files with special characters in names

The script handles Unicode characters automatically. This includes:
- Japanese characters (ひらがな, カタカナ, 漢字)
- Emojis
- Accented characters
- Other Unicode scripts

### "Permission denied" error

Make sure you have write access to the directory. Run the script with appropriate permissions or choose a different directory.

### Files not moving on Windows

- Ensure the directory isn't locked by another program
- Check that you're not organizing system directories (use a regular folder)
- Files marked as read-only might need permission changes

## Command-Line Options Reference

```
python file_organizer.py [directory]

directory (optional)  - Full path to the folder to organize
                       Example: python file_organizer.py "C:\Downloads"
```

When run without arguments, the script enters interactive mode and prompts for all required information.

## API Usage (Advanced)

You can also import the module in your Python code:

```python
from file_organizer import organize_files, cluster_files

# Organize files with custom threshold
result = organize_files(
    source_dir="./my_files",
    threshold=0.75,
    dry_run=False,
    exclude_system_files=True
)

# Just cluster files without organizing
clusters = cluster_files([
    "file1_v1.txt",
    "file1_v2.txt",
    "file2_v1.txt"
], threshold=0.7)
```

## Platform Support

- ✅ Windows (XP SP3+)
- ✅ macOS (10.9+)
- ✅ Linux (All distributions)

## License

See LICENSE file for details.

## Contributing

Suggestions and improvements welcome!

## Notes

- The script creates folders at the same level as the files being organized
- Original files are moved (not copied) into the new folders
- Folder names are automatically sanitized for filesystem compatibility
- The operation is atomic per group (if a file fails, it won't retry, but other groups continue)
