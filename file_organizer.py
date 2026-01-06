#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuzzy File Organizer - Groups files with similar names using fuzzy matching
Supports Japanese and all Unicode character sets
"""

import os
import shutil
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict
from typing import List, Tuple, Set, Dict, Union
import sys
import logging
import platform
import re

# Detect Windows platform
IS_WINDOWS = sys.platform.startswith('win')

# Set console encoding for Windows to support Unicode
if IS_WINDOWS:
    try:
        # Enable UTF-8 output on Windows console
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)  # Input
        kernel32.SetConsoleOutputCP(65001)  # Output
    except Exception:
        pass  # Fallback if unable to set encoding

# Configure logging with proper encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    encoding='utf-8' if IS_WINDOWS else None
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SIMILARITY_THRESHOLD = 0.7
MIN_THRESHOLD = 0.5
MAX_THRESHOLD = 0.95
MIN_CLUSTER_SIZE = 2

# Version pattern to match: v1, ver1, v.1, ver.1, .1, v1.0.0, ver1.0.0, v.1.0.0, .1.0.0, etc.
# Supports: v1, ver1, v.1, ver.1, .1, v1.0, ver1.0, etc. with optional underscore/whitespace prefix
VERSION_PATTERN = r'[_\s]?(?:(?:v|ver)\.?\d+|\.\d+)(?:\.\d+)?(?:\.\d+)?'
# Marker pattern to match: final, draft, beta, alpha, rc (with optional underscore/whitespace prefix)
# Using word boundaries to avoid matching partial words like "rc" in "archive"
MARKER_PATTERN = r'[_\s]?(final|draft|beta|alpha|rc)(?=\.|$|[_\s])'

# Windows reserved filenames (case-insensitive)
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

# Invalid characters - Windows is stricter than Unix
INVALID_FOLDER_CHARS = '<>:"/\\|?*'
EXCLUDED_EXTENSIONS = {'.exe', '.dll', '.sys', '.tmp', '.lnk'}
SEPARATOR_WIDTH = 60
MAX_PATH_LENGTH = 255  # Windows MAX_PATH limitation

def normalize_filename(filename: str) -> str:
    """
    Normalize a filename by removing version patterns and file extensions.
    
    Removes:
    - Version patterns: v1, ver1, .1, v.1, ver.1, v1.0, ver1.0, v1.0.0, ver1.0.0, etc. (with optional prefix)
    - Version markers: final, draft, beta, alpha, rc (with optional prefix)
    - File extensions: .txt, .pdf, etc.
    
    Examples:
        'report_v1.0.0.pdf' -> 'report'
        'readme_ver2.3.1.txt' -> 'readme'
        'photo_v.1.0.0.jpg' -> 'photo'
        'document_.1.2.0.pdf' -> 'document'
        'photo_final.jpg' -> 'photo'
        'readme_v1.txt' -> 'readme'
    
    Args:
        filename: The filename to normalize
        
    Returns:
        Normalized filename without version patterns, markers, or extensions
    """
    if not filename:
        return ""
    
    # Remove file extension
    normalized = os.path.splitext(filename)[0]
    
    # Remove version patterns (e.g., v1.0.0, _v1.0.0, " v1.0.0")
    normalized = re.sub(VERSION_PATTERN, '', normalized, flags=re.IGNORECASE)
    
    # Remove version markers (e.g., final, draft, beta, alpha, rc)
    normalized = re.sub(MARKER_PATTERN, '', normalized, flags=re.IGNORECASE)
    
    # Clean up any trailing underscores or spaces left after removal
    normalized = normalized.rstrip('_ ')
    
    return normalized

def similarity_ratio(str1: str, str2: str) -> float:
    """
    Calculate similarity ratio between two strings.
    
    Uses normalized strings (without version patterns or extensions) for comparison.
    
    Args:
        str1: First string to compare
        str2: Second string to compare
        
    Returns:
        Similarity ratio between 0.0 and 1.0 (1.0 being identical)
    """
    # Normalize both filenames before comparison
    normalized_str1 = normalize_filename(str1)
    normalized_str2 = normalize_filename(str2)
    
    return SequenceMatcher(None, normalized_str1.lower(), normalized_str2.lower()).ratio()

def get_representative_name(filenames: List[str]) -> str:
    """
    Get the most representative base name from a group of filenames.
    
    Prefers the cleanest name (without version patterns or markers).
    If multiple files have equally clean names, uses the one with highest average
    similarity to other names as representative (centroid approach).
    
    Args:
        filenames: List of filenames to analyze
        
    Returns:
        The most representative base name without extension, version patterns, or markers
        
    Raises:
        ValueError: If the filenames list is empty
    """
    if not filenames:
        raise ValueError("Filenames list cannot be empty")
    
    # Remove extensions and normalize to get clean base names
    normalized_names = [normalize_filename(f) for f in filenames]
    
    # Find the name with most similarity to others (centroid) among normalized names
    best_name = ""
    best_score = 0.0
    
    for name in normalized_names:
        score = sum(similarity_ratio(name, other) for other in normalized_names)
        if score > best_score:
            best_score = score
            best_name = name
    
    # Clean up the name for folder use
    if not best_name:
        best_name = normalized_names[0] if normalized_names else "Files"
    
    return best_name.strip()

def cluster_files(files: List[str], threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> List[List[str]]:
    """
    Group files by name similarity using fuzzy matching.
    
    Creates clusters of files where each pair has similarity >= threshold.
    
    Args:
        files: List of file paths to cluster
        threshold: Similarity threshold between 0.0 and 1.0
        
    Returns:
        List of clusters, where each cluster is a list of file paths
        
    Raises:
        ValueError: If threshold is not between 0.0 and 1.0
    """
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
    
    clusters = []
    used: Set[int] = set()
    
    for i, file1 in enumerate(files):
        if i in used:
            continue
        
        cluster = [file1]
        used.add(i)
        
        for j, file2 in enumerate(files[i+1:], i+1):
            if j in used:
                continue
            
            # Calculate similarity between filenames (without path)
            name1 = os.path.basename(file1)
            name2 = os.path.basename(file2)
            
            if similarity_ratio(name1, name2) >= threshold:
                cluster.append(file2)
                used.add(j)
        
        # Only create clusters with 2+ files
        if len(cluster) >= MIN_CLUSTER_SIZE:
            clusters.append(cluster)
    
    return clusters

def sanitize_folder_name(name: str) -> str:
    """
    Remove or replace characters that are invalid in folder names.
    
    Handles Windows-specific restrictions including:
    - Invalid characters: < > : " / \\ | ? *
    - Reserved names: CON, PRN, AUX, NUL, COM1-9, LPT1-9
    - Leading/trailing spaces and dots (Windows limitation)
    
    Args:
        name: The folder name to sanitize
        
    Returns:
        Sanitized folder name safe for filesystem operations (Windows-safe)
    """
    if not name:
        return "Files"
    
    sanitized = name
    
    # Replace invalid characters
    for char in INVALID_FOLDER_CHARS:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing spaces and dots (Windows restriction)
    sanitized = sanitized.strip(' .')
    
    # Check for Windows reserved names
    if IS_WINDOWS:
        # Split to check base name before extension
        base_name = os.path.splitext(sanitized)[0]
        if base_name.upper() in WINDOWS_RESERVED_NAMES:
            sanitized = f"__{sanitized}"  # Prefix reserved names
    
    # Limit folder name length (Windows: 255 chars, leave buffer)
    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip(' .')
    
    return sanitized or "Files"  # Fallback if everything was invalid

def should_exclude_file(file_path: Union[str, Path]) -> bool:
    """
    Determine if a file should be excluded from organization.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file should be excluded, False otherwise
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path
    extension = path.suffix.lower()
    return extension in EXCLUDED_EXTENSIONS

def organize_files(source_dir: Union[str, Path], 
                   threshold: float = DEFAULT_SIMILARITY_THRESHOLD, 
                   dry_run: bool = True,
                   exclude_system_files: bool = True) -> bool:
    """
    Organize files in source_dir by creating folders for similar filenames.
    
    Groups files with similar names and moves them into descriptively-named folders.
    Performs a dry run first to show preview, then asks for confirmation before moving.
    
    Windows-compatible with proper handling of:
    - UNC paths
    - Long paths (260+ characters)
    - Reserved filenames
    - Unicode characters
    - File system permissions
    
    Args:
        source_dir: Path to directory containing files to organize
        threshold: Similarity threshold between 0.5 and 0.95 (default 0.7)
        dry_run: If True, only preview without moving files
        exclude_system_files: If True, exclude system file types (.exe, .dll, etc.)
        
    Returns:
        True if operation completed successfully, False otherwise
        
    Raises:
        ValueError: If source_dir doesn't exist or threshold is invalid
    """
    try:
        source_path = Path(source_dir)
        
        # Validate directory
        if not source_path.exists():
            logger.error(f"Error: Directory '{source_dir}' does not exist")
            return False
        
        if not source_path.is_dir():
            logger.error(f"Error: '{source_dir}' is not a directory")
            return False
        
        # Validate threshold
        if not (MIN_THRESHOLD <= threshold <= MAX_THRESHOLD):
            logger.error(f"Error: Threshold must be between {MIN_THRESHOLD} and {MAX_THRESHOLD}")
            return False
        
    except Exception as e:
        logger.error(f"Error accessing directory: {e}")
        return False
    
    # Get all files (not directories)
    try:
        all_files = [f for f in source_path.iterdir() if f.is_file()]
        
        if exclude_system_files:
            all_files = [f for f in all_files if not should_exclude_file(f)]
        
    except PermissionError:
        logger.error(f"Permission denied accessing '{source_dir}'")
        return False
    
    if not all_files:
        logger.info("No files found in directory")
        return False
    
    logger.info(f"\nFound {len(all_files)} files")
    logger.info(f"Using similarity threshold: {threshold}")
    logger.info(f"{'='*SEPARATOR_WIDTH}\n")
    
    # Convert to strings for processing
    file_paths = [str(f) for f in all_files]
    
    # Cluster similar files
    try:
        clusters = cluster_files(file_paths, threshold)
    except ValueError as e:
        logger.error(f"Error clustering files: {e}")
        return False
    
    if not clusters:
        logger.info("No similar file groups found. Try lowering the threshold.")
        return False
    
    logger.info(f"Found {len(clusters)} groups of similar files:\n")
    
    # Preview clusters
    for i, cluster in enumerate(clusters, 1):
        filenames = [os.path.basename(f) for f in cluster]
        folder_name = sanitize_folder_name(get_representative_name(filenames))
        
        logger.info(f"Group {i}: '{folder_name}' ({len(cluster)} files)")
        for filename in filenames:
            logger.info(f"  • {filename}")
        logger.info("")
    
    # Calculate summary statistics
    files_in_clusters = sum(len(cluster) for cluster in clusters)
    orphaned_files = len(all_files) - files_in_clusters
    
    logger.info("="*SEPARATOR_WIDTH)
    logger.info("SUMMARY")
    logger.info("="*SEPARATOR_WIDTH)
    logger.info(f"Total files:              {len(all_files)}")
    logger.info(f"Groups found:             {len(clusters)}")
    logger.info(f"Files to organize:        {files_in_clusters}")
    logger.info(f"Orphaned files:           {orphaned_files}")
    logger.info("="*SEPARATOR_WIDTH)
    
    if dry_run:
        logger.info("This was a preview. No files were moved.")
        logger.info("To actually organize the files, run with dry_run=False")
        return True
    
    # Actually move files
    logger.info("="*SEPARATOR_WIDTH)
    response = input("Proceed with organizing files? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        logger.info("Cancelled.")
        return False
    
    files_moved = 0
    errors = 0
    
    for cluster_idx, cluster in enumerate(clusters, 1):
        filenames = [os.path.basename(f) for f in cluster]
        folder_name = sanitize_folder_name(get_representative_name(filenames))
        target_folder = source_path / folder_name
        
        try:
            # Create folder
            target_folder.mkdir(exist_ok=True)
            
            # Move files
            for file_path in cluster:
                src = Path(file_path)
                dst = target_folder / src.name
                
                try:
                    # Handle name collisions
                    if dst.exists():
                        base = dst.stem
                        ext = dst.suffix
                        counter = 1
                        while dst.exists():
                            dst = target_folder / f"{base}_{counter}{ext}"
                            counter += 1
                    
                    shutil.move(str(src), str(dst))
                    logger.info(f"Moved: {src.name} → {folder_name}/")
                    files_moved += 1
                    
                except Exception as e:
                    logger.error(f"Failed to move {src.name}: {e}")
                    errors += 1
                    
        except Exception as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            errors += 1
    
    logger.info(f"\n✓ Successfully organized {files_moved} files into {len(clusters)} folders")
    if errors > 0:
        logger.warning(f"⚠ {errors} file(s) had errors during organization")
    
    return errors == 0

def get_user_threshold() -> float:
    """
    Get and validate threshold input from user.
    
    Returns:
        Valid threshold between MIN_THRESHOLD and MAX_THRESHOLD
    """
    while True:
        try:
            threshold_input = input(f"Enter similarity threshold ({MIN_THRESHOLD}-{MAX_THRESHOLD}, default {DEFAULT_SIMILARITY_THRESHOLD}): ").strip()
            threshold = float(threshold_input) if threshold_input else DEFAULT_SIMILARITY_THRESHOLD
            
            if not (MIN_THRESHOLD <= threshold <= MAX_THRESHOLD):
                logger.warning(f"Threshold must be between {MIN_THRESHOLD} and {MAX_THRESHOLD}")
                continue
            
            return threshold
            
        except ValueError:
            logger.warning("Invalid input. Please enter a valid number.")
            continue

def get_user_directory() -> Union[str, None]:
    """
    Get and validate directory path from user.
    
    Supports both Windows and Unix paths, including:
    - UNC paths on Windows (\\\\server\\share)
    - Tilde expansion (~) for home directory
    - Relative paths
    - Drive letters on Windows (C:, D:, etc.)
    
    Returns:
        Valid directory path or None if user cancels
    """
    hint = " (e.g., C:\\\\Downloads or ~\\\\Downloads)"
    
    while True:
        directory = input(f"Enter the path to your folder (press Enter to use current directory, or 'quit' to exit){hint}:\\n> ").strip()
        
        if directory.lower() in ['quit', 'q', 'exit']:
            return None
        
        if not directory:
            directory = os.getcwd()
            logger.info(f"Using current directory: {directory}")
        
        # Expand user home directory (~)
        directory = os.path.expanduser(directory)
        
        # On Windows, support forward slashes (convert to backslashes internally)
        if IS_WINDOWS:
            directory = directory.replace('/', '\\')
        
        try:
            path = Path(directory)
            
            # Resolve to absolute path
            path = path.resolve()
            
            if not path.exists():
                logger.warning(f"Directory does not exist: {directory}")
                continue
            
            if not path.is_dir():
                logger.warning(f"Not a directory: {directory}")
                continue
            
            # Test write access
            test_file = path / ".fileorg_test"
            try:
                test_file.touch()
                test_file.unlink()
            except PermissionError:
                logger.warning(f"No write permission in: {directory}")
                continue
            
            return str(path)
            
        except Exception as e:
            logger.warning(f"Invalid path: {e}")
            continue

def main() -> int:
    """
    Main entry point for the file organizer.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("Fuzzy File Organizer")
    logger.info("="*SEPARATOR_WIDTH)
    
    # Show platform info
    if IS_WINDOWS:
        logger.info(f"Running on Windows {platform.release()}")
        logger.info("UTF-8 encoding enabled for console")
    else:
        logger.info(f"Running on {platform.system()}")
    logger.info("="*SEPARATOR_WIDTH + "\n")
    
    # Get directory from user or command line
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = get_user_directory()
        if directory is None:
            logger.info("Exiting...")
            return 1
    
    # Get threshold
    threshold = get_user_threshold()
    
    # Run preview first
    while True:
        logger.info("\n" + "="*SEPARATOR_WIDTH)
        logger.info("PREVIEW MODE - No files will be moved")
        logger.info("="*SEPARATOR_WIDTH)
        
        success = organize_files(directory, threshold=threshold, dry_run=True)
        
        if not success:
            # Ask if user wants to adjust threshold
            logger.info("\n" + "="*SEPARATOR_WIDTH)
            response = input("\nNo similar groups found. Would you like to:\n1. Adjust similarity ratio\n2. Cancel\nEnter your choice (1-2): ").strip().lower()
            
            if response in ['1']:
                logger.info(f"Current threshold: {threshold}")
                threshold = get_user_threshold()
                continue
            else:
                logger.info("Cancelled.")
                return 1
        
        # Ask if user wants to proceed or adjust threshold
        logger.info("\n" + "="*SEPARATOR_WIDTH)
        response = input("\nWhat would you like to do?\n1. Organize files now\n2. Adjust similarity ratio\n3. Cancel\nEnter your choice (1-3): ").strip().lower()
        
        if response in ['1', 'yes', 'y']:
            success = organize_files(directory, threshold=threshold, dry_run=False)
            return 0 if success else 1
        elif response in ['2']:
            logger.info(f"Current threshold: {threshold}")
            threshold = get_user_threshold()
            continue
        else:
            logger.info("Cancelled.")
            return 1


if __name__ == "__main__":
    sys.exit(main())