"""
Pytest configuration and fixtures for file organizer tests.
"""

import pytest
from pathlib import Path
import shutil


@pytest.fixture
def fixtures_path():
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_files_path(fixtures_path):
    """Return the path to pre-generated sample files."""
    return fixtures_path / "sample_files"


@pytest.fixture
def tmp_test_dir(tmp_path):
    """Create a temporary test directory with empty structure."""
    return tmp_path


@pytest.fixture
def test_dir_with_samples(tmp_path, sample_files_path):
    """
    Copy pre-generated sample files to a temporary test directory.
    
    Returns the temporary directory path with sample files ready for testing.
    """
    if sample_files_path.exists():
        for sample_file in sample_files_path.iterdir():
            if sample_file.is_file():
                shutil.copy2(sample_file, tmp_path / sample_file.name)
    
    return tmp_path


@pytest.fixture
def assert_organized_files():
    """
    Factory fixture that returns a helper function to validate file organization.
    
    This checks that:
    - Files are moved into expected folders
    - Folder names match expected patterns
    - Original files are removed from root
    """
    def _validate(directory, expected_folders, expected_file_mapping):
        """
        Validate file organization.
        
        Args:
            directory: Path to the organized directory
            expected_folders: Set/list of expected folder names
            expected_file_mapping: Dict mapping expected folder names to file lists
                                  e.g., {"photo": ["photo_v1.jpg", "photo_v2.jpg"]}
        
        Returns:
            True if validation passes, raises AssertionError otherwise
        """
        dir_path = Path(directory)
        
        # Check expected folders exist
        actual_folders = {d.name for d in dir_path.iterdir() if d.is_dir()}
        for expected_folder in expected_folders:
            assert expected_folder in actual_folders, \
                f"Expected folder '{expected_folder}' not found. Found: {actual_folders}"
        
        # Check file locations
        for folder_name, expected_files in expected_file_mapping.items():
            folder_path = dir_path / folder_name
            assert folder_path.exists() and folder_path.is_dir(), \
                f"Folder '{folder_name}' not found or is not a directory"
            
            actual_files = {f.name for f in folder_path.iterdir() if f.is_file()}
            
            for expected_file in expected_files:
                assert expected_file in actual_files, \
                    f"Expected file '{expected_file}' not found in '{folder_name}'. " \
                    f"Found: {actual_files}"
        
        # Check no files remain in root
        root_files = [f for f in dir_path.iterdir() if f.is_file()]
        assert len(root_files) == 0, \
            f"Found {len(root_files)} files in root directory; all should be organized"
        
        return True
    
    return _validate


@pytest.fixture
def assert_folder_name_valid():
    """
    Factory fixture that returns a helper function to validate folder names.
    
    Checks that folder names don't contain invalid Windows characters
    and aren't Windows reserved names.
    """
    def _validate(folder_name):
        """
        Validate that a folder name is Windows-safe.
        
        Args:
            folder_name: The folder name to validate
            
        Returns:
            True if valid, raises AssertionError otherwise
        """
        invalid_chars = '<>:"/\\|?*'
        reserved_names = {'CON', 'PRN', 'AUX', 'NUL',
                         'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
                         'COM6', 'COM7', 'COM8', 'COM9',
                         'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
                         'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        
        for char in invalid_chars:
            assert char not in folder_name, \
                f"Folder name contains invalid character: '{char}'"
        
        base_name = Path(folder_name).stem
        assert base_name.upper() not in reserved_names, \
            f"Folder name is a Windows reserved name: {base_name}"
        
        assert not folder_name.startswith((' ', '.')), \
            "Folder name cannot start with space or dot"
        
        assert not folder_name.endswith((' ', '.')), \
            "Folder name cannot end with space or dot"
        
        return True
    
    return _validate
