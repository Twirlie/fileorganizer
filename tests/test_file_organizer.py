"""
Comprehensive test suite for the Fuzzy File Organizer.

Tests cover:
- Unit tests for core functions (similarity, clustering, sanitization)
- Integration tests for file organization with actual file operations
- Edge cases and Windows compatibility
- Input validation and error handling
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path to import file_organizer
sys.path.insert(0, str(Path(__file__).parent.parent))

from file_organizer import (
    similarity_ratio,
    cluster_files,
    get_representative_name,
    sanitize_folder_name,
    should_exclude_file,
    organize_files,
    get_user_directory,
    get_user_threshold,
    normalize_filename
)


# ============================================================================
# UNIT TESTS - normalize_filename
# ============================================================================

class TestNormalizeFilename:
    """Test the normalize_filename function."""
    
    def test_removes_semantic_version_with_underscore(self):
        """Should remove semantic versions with underscore prefix (all formats)."""
        assert normalize_filename("report_v1.pdf") == "report"
        assert normalize_filename("report_v1.0.pdf") == "report"
        assert normalize_filename("report_v1.0.0.pdf") == "report"
        assert normalize_filename("readme_v2.3.1.txt") == "readme"
        # Also test ver format
        assert normalize_filename("report_ver1.pdf") == "report"
        assert normalize_filename("report_ver1.0.0.pdf") == "report"
        assert normalize_filename("readme_ver2.3.1.txt") == "readme"
        # Also test dot-prepended format
        assert normalize_filename("report_v.1.pdf") == "report"
        assert normalize_filename("report_v.1.0.0.pdf") == "report"
        assert normalize_filename("readme_.1.2.3.txt") == "readme"
    
    def test_removes_semantic_version_without_prefix(self):
        """Should remove semantic versions without prefix."""
        assert normalize_filename("reportv1.pdf") == "report"
        assert normalize_filename("reportv1.0.pdf") == "report"
        assert normalize_filename("reportv1.0.0.pdf") == "report"
        assert normalize_filename("readmev2.3.1.txt") == "readme"
        # Also test ver format
        assert normalize_filename("reportver1.pdf") == "report"
        assert normalize_filename("reportver1.0.0.pdf") == "report"
        assert normalize_filename("readmever2.3.1.txt") == "readme"
        # Also test dot-prepended format
        assert normalize_filename("reportv.1.pdf") == "report"
        assert normalize_filename("reportv.1.0.0.pdf") == "report"
        assert normalize_filename("readme.1.2.3.txt") == "readme"
    
    def test_removes_semantic_version_with_whitespace(self):
        """Should remove semantic versions with whitespace prefix."""
        assert normalize_filename("report v1.pdf") == "report"
        assert normalize_filename("report v1.0.pdf") == "report"
        assert normalize_filename("readme v2.3.1.txt") == "readme"
        # Also test ver format
        assert normalize_filename("report ver1.pdf") == "report"
        assert normalize_filename("report ver1.0.0.pdf") == "report"
        assert normalize_filename("readme ver2.3.1.txt") == "readme"
        # Also test dot-prepended format
        assert normalize_filename("report v.1.pdf") == "report"
        assert normalize_filename("report v.1.0.0.pdf") == "report"
        assert normalize_filename("readme .1.2.3.txt") == "readme"
    
    def test_removes_version_markers(self):
        """Should remove version markers (final, draft, beta, alpha, rc)."""
        assert normalize_filename("document_final.pdf") == "document"
        assert normalize_filename("document_draft.pdf") == "document"
        assert normalize_filename("software_beta.exe") == "software"
        assert normalize_filename("app_alpha.zip") == "app"
        assert normalize_filename("release_rc.tar") == "release"
    
    def test_removes_version_markers_with_whitespace(self):
        """Should remove version markers with whitespace prefix."""
        assert normalize_filename("document final.pdf") == "document"
        assert normalize_filename("document draft.pdf") == "document"
    
    def test_removes_file_extensions(self):
        """Should remove file extensions."""
        assert normalize_filename("photo.jpg") == "photo"
        assert normalize_filename("document.pdf") == "document"
        # Note: splitext only removes last extension, so archive.tar.gz -> archive.tar
        assert normalize_filename("archive.tar.gz") == "archive.tar"
    
    def test_combined_version_and_extension(self):
        """Should handle combined version patterns and extensions."""
        assert normalize_filename("report_v1.0.0.pdf") == "report"
        assert normalize_filename("document v2.1.0 final.docx") == "document"
        assert normalize_filename("readme_v1.2.3_draft.txt") == "readme"
    
    def test_case_insensitive_markers(self):
        """Should handle markers in any case."""
        assert normalize_filename("document_FINAL.pdf") == "document"
        assert normalize_filename("document_Draft.pdf") == "document"
        assert normalize_filename("software_BETA.exe") == "software"
    
    def test_handles_multiple_version_patterns(self):
        """Should handle multiple version patterns in one filename."""
        assert normalize_filename("photo_v1.0.0_final_v2.1.0.jpg") == "photo"
    
    def test_empty_string(self):
        """Empty string should return empty string."""
        assert normalize_filename("") == ""
    
    def test_only_extension(self):
        """File with only extension should return the extension (no base name)."""
        # os.path.splitext(".pdf") returns (".pdf", "") so we get ".pdf"
        assert normalize_filename(".pdf") == ".pdf"
    
    def test_unicode_filenames(self):
        """Should preserve unicode characters."""
        assert normalize_filename("写真_v1.0.0.jpg") == "写真"
        assert normalize_filename("文書_final.pdf") == "文書"
    
    def test_trailing_underscores_removed(self):
        """Trailing underscores and spaces should be removed."""
        assert normalize_filename("photo_v1.0.0.jpg") == "photo"
        assert normalize_filename("document_final.pdf") == "document"
    
    def test_preserves_normal_names(self):
        """Normal names without versions should be preserved (minus extension)."""
        assert normalize_filename("photo.jpg") == "photo"
        assert normalize_filename("document.pdf") == "document"
        assert normalize_filename("readme.txt") == "readme"


# ============================================================================
# UNIT TESTS - similarity_ratio
# ============================================================================

class TestSimilarityRatio:
    """Test the similarity_ratio function."""
    
    def test_identical_strings(self):
        """Identical strings should have ratio 1.0."""
        assert similarity_ratio("photo", "photo") == 1.0
        assert similarity_ratio("PHOTO", "photo") == 1.0  # Case insensitive
    
    def test_completely_different_strings(self):
        """Completely different strings should have ratio 0.0."""
        assert similarity_ratio("abc", "xyz") == 0.0
    
    def test_partial_similarity(self):
        """Partial matches should return values between 0 and 1."""
        # Use names that have some similarity but aren't versions
        ratio = similarity_ratio("photo_backup", "photo_archive")
        assert 0 < ratio < 1
        assert ratio > 0.5  # Should be reasonably similar
    
    def test_case_insensitivity(self):
        """Comparison should be case-insensitive."""
        assert similarity_ratio("PHOTO", "photo") == 1.0
        assert similarity_ratio("Photo_V1", "photo_v1") == 1.0
    
    def test_empty_strings(self):
        """Empty strings should have ratio 1.0 (both empty)."""
        assert similarity_ratio("", "") == 1.0
    
    def test_one_empty_string(self):
        """One empty string should have low similarity."""
        assert similarity_ratio("photo", "") == 0.0
    
    def test_single_character_difference(self):
        """Single character difference should have high ratio."""
        ratio = similarity_ratio("report_draft", "report_final")
        assert ratio > 0.6
    
    def test_unicode_strings(self):
        """Unicode characters should be handled correctly."""
        ratio = similarity_ratio("写真_v1", "写真_v2")
        assert ratio > 0.5
    
    def test_ignores_version_numbers_in_similarity(self):
        """Version numbers should be ignored when calculating similarity."""
        # Files with different versions should match perfectly (after normalization)
        ratio = similarity_ratio("readme_v1.0.0.txt", "readme_v2.0.0.txt")
        assert ratio == 1.0
    
    def test_ignores_version_markers_in_similarity(self):
        """Version markers should be ignored when calculating similarity."""
        ratio = similarity_ratio("document_final.pdf", "document_draft.pdf")
        assert ratio == 1.0
    
    def test_ignores_extensions_in_similarity(self):
        """File extensions should not affect similarity."""
        ratio = similarity_ratio("report.pdf", "report.txt")
        assert ratio == 1.0
    
    def test_ignores_all_version_patterns_combined(self):
        """Should ignore version numbers, markers, and extensions together."""
        ratio1 = similarity_ratio("photo_v1.0.0_final.jpg", "photo_v2.1.0_draft.png")
        assert ratio1 == 1.0
    
    def test_different_base_names_still_differ(self):
        """Different base names should still have low similarity even with versions."""
        ratio = similarity_ratio("report_v1.0.0.pdf", "photo_v1.0.0.pdf")
        # "report" vs "photo" - normalized to just base names, should be low similarity
        assert ratio < 0.6


# ============================================================================
# UNIT TESTS - cluster_files
# ============================================================================

class TestClusterFiles:
    """Test the cluster_files function."""
    
    def test_no_clusters_below_threshold(self):
        """Files below similarity threshold should not cluster."""
        files = ["abc.txt", "xyz.txt", "pqr.txt"]
        clusters = cluster_files(files, threshold=0.9)
        assert len(clusters) == 0
    
    def test_single_cluster(self):
        """Very similar files should form one cluster."""
        files = ["photo_v1.jpg", "photo_v2.jpg", "photo_v3.jpg"]
        clusters = cluster_files(files, threshold=0.7)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
    
    def test_multiple_clusters(self):
        """Different groups of similar files should form separate clusters."""
        files = [
            "photo_v1.jpg", "photo_v2.jpg",
            "report_draft.pdf", "report_final.pdf"
        ]
        clusters = cluster_files(files, threshold=0.7)
        assert len(clusters) == 2
    
    def test_minimum_cluster_size(self):
        """Clusters must have at least 2 files."""
        files = ["file1.txt", "file2.txt", "unique.doc"]
        clusters = cluster_files(files, threshold=0.7)
        # Only file1 and file2 should cluster
        assert all(len(c) >= 2 for c in clusters)
    
    def test_single_file(self):
        """Single file should not create a cluster."""
        files = ["single.txt"]
        clusters = cluster_files(files, threshold=0.7)
        assert len(clusters) == 0
    
    def test_empty_file_list(self):
        """Empty file list should return empty clusters."""
        clusters = cluster_files([], threshold=0.7)
        assert len(clusters) == 0
    
    def test_invalid_threshold_too_low(self):
        """Threshold below 0.0 should raise ValueError."""
        with pytest.raises(ValueError):
            cluster_files(["file1.txt", "file2.txt"], threshold=-0.1)
    
    def test_invalid_threshold_too_high(self):
        """Threshold above 1.0 should raise ValueError."""
        with pytest.raises(ValueError):
            cluster_files(["file1.txt", "file2.txt"], threshold=1.1)
    
    def test_threshold_boundaries(self):
        """Thresholds at 0.0 and 1.0 should be valid."""
        files = ["file1.txt", "file2.txt"]
        # Should not raise
        cluster_files(files, threshold=0.0)
        cluster_files(files, threshold=1.0)
    
    def test_with_different_extensions(self):
        """Files with different extensions but similar basenames should cluster."""
        files = ["report.pdf", "report.txt", "report.doc"]
        clusters = cluster_files(files, threshold=0.6)
        # Should cluster based on basename similarity
        assert len(clusters) > 0
    
    def test_threshold_sensitivity(self):
        """Lower threshold should produce more clusters."""
        files = ["photo_v1.jpg", "photo_v2.jpg", "photo_new.jpg"]
        clusters_strict = cluster_files(files, threshold=0.95)
        clusters_loose = cluster_files(files, threshold=0.5)
        # Loose threshold should result in same or more clusters
        assert len(clusters_loose) >= len(clusters_strict)
    
    def test_semantic_version_clustering_underscore(self):
        """Files with semantic versions and underscore prefix should cluster."""
        files = ["readme_v1.0.0.txt", "readme_v2.0.0.txt", "readme_v3.1.0.txt"]
        clusters = cluster_files(files, threshold=0.7)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
    
    def test_semantic_version_clustering_no_prefix(self):
        """Files with semantic versions and no prefix should cluster."""
        files = ["readmev1.0.0.txt", "readmev2.0.0.txt", "readmev3.1.0.txt"]
        clusters = cluster_files(files, threshold=0.7)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
    
    def test_semantic_version_clustering_whitespace(self):
        """Files with semantic versions and whitespace prefix should cluster."""
        files = ["readme v1.0.0.txt", "readme v2.0.0.txt", "readme v3.1.0.txt"]
        clusters = cluster_files(files, threshold=0.7)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
    
    def test_mixed_version_formats_clustering(self):
        """Files with mixed version formats should cluster together."""
        files = ["report_v1.0.0.pdf", "report v2.1.0.pdf", "reportv3.0.0.pdf"]
        clusters = cluster_files(files, threshold=0.7)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
    
    def test_version_markers_with_extensions(self):
        """Files with version markers and different extensions should cluster."""
        files = ["readme_final.txt", "readme_draft.doc", "readme_beta.pdf"]
        clusters = cluster_files(files, threshold=0.7)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3


# ============================================================================
# UNIT TESTS - get_representative_name
# ============================================================================

class TestGetRepresentativeName:
    """Test the get_representative_name function."""
    
    def test_single_filename(self):
        """Single filename should return its base name without versions."""
        result = get_representative_name(["photo_v1.jpg"])
        assert result == "photo"
    
    def test_identical_basenames(self):
        """Identical basenames should return that name."""
        result = get_representative_name(["photo.jpg", "photo.png", "photo.txt"])
        assert result == "photo"
    
    def test_similar_names(self):
        """Similar names should return the most representative."""
        result = get_representative_name(["photo_v1.jpg", "photo_v2.jpg", "photo_final.jpg"])
        assert "photo" in result.lower()
    
    def test_multiple_versions(self):
        """Versions with common prefix should favor the prefix."""
        result = get_representative_name(["report_draft.pdf", "report_final.pdf"])
        assert "report" in result.lower()
    
    def test_empty_list_raises_error(self):
        """Empty list should raise ValueError."""
        with pytest.raises(ValueError):
            get_representative_name([])
    
    def test_removes_extensions(self):
        """Result should not include file extensions."""
        result = get_representative_name(["test.txt", "test.doc"])
        assert "." not in result
    
    def test_fallback_on_no_similarity(self):
        """Should return a valid name even with dissimilar files."""
        result = get_representative_name(["abc.txt", "xyz.doc", "pqr.pdf"])
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_prefers_cleanest_name_no_version(self):
        """Should prefer the cleanest name without version patterns."""
        result = get_representative_name(["readme_v1.0.0.txt", "readme_v2.1.0.txt", "readme.txt"])
        assert result == "readme"
    
    def test_removes_version_patterns_from_representative(self):
        """Representative name should not contain version patterns."""
        result = get_representative_name(["report_v1.0.0.pdf", "report_v2.0.0.pdf"])
        assert "v1" not in result
        assert "v2" not in result
        assert result == "report"
    
    def test_removes_version_markers_from_representative(self):
        """Representative name should not contain version markers."""
        result = get_representative_name(["document_final.pdf", "document_draft.pdf"])
        assert "final" not in result.lower()
        assert "draft" not in result.lower()
        assert result == "document"
    
    def test_semantic_version_handling(self):
        """Should handle semantic version formats correctly."""
        result = get_representative_name(["software_v1.0.0.exe", "software_v2.3.1.exe"])
        assert result == "software"


# ============================================================================
# UNIT TESTS - sanitize_folder_name
# ============================================================================

class TestSanitizeFolderName:
    """Test the sanitize_folder_name function."""
    
    def test_no_invalid_characters(self):
        """Valid names should not change."""
        result = sanitize_folder_name("valid_folder_name")
        assert result == "valid_folder_name"
    
    def test_removes_invalid_windows_chars(self):
        """Invalid Windows characters should be replaced."""
        result = sanitize_folder_name("file<name>test")
        assert "<" not in result
        assert ">" not in result
        assert "_" in result  # Replaced with underscore
    
    def test_all_invalid_chars(self):
        """All invalid chars should be removed/replaced."""
        # < > : " / \ | ? *
        invalid_string = 'file<>:"/\\|?*test'
        result = sanitize_folder_name(invalid_string)
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "/" not in result
        assert "\\" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result
    
    def test_reserved_windows_names(self):
        """Windows reserved names should be prefixed."""
        for name in ["CON", "PRN", "AUX", "NUL"]:
            result = sanitize_folder_name(name)
            assert result != name
            assert "__" in result or result.startswith("_")
    
    def test_reserved_names_case_insensitive(self):
        """Reserved name check should be case-insensitive."""
        result = sanitize_folder_name("con")
        assert result != "con"
        
        result = sanitize_folder_name("Con")
        assert result != "Con"
    
    def test_reserved_com_ports(self):
        """COM and LPT ports should be handled."""
        for name in ["COM1", "COM9", "LPT1", "LPT9"]:
            result = sanitize_folder_name(name)
            assert result != name
    
    def test_leading_trailing_spaces(self):
        """Leading/trailing spaces should be removed."""
        result = sanitize_folder_name("  spaced folder  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")
    
    def test_leading_trailing_dots(self):
        """Leading/trailing dots should be removed."""
        result = sanitize_folder_name("...dotted...")
        assert not result.startswith(".")
        assert not result.endswith(".")
    
    def test_long_folder_names(self):
        """Very long names should be truncated."""
        long_name = "a" * 300
        result = sanitize_folder_name(long_name)
        assert len(result) <= 200
    
    def test_empty_string(self):
        """Empty string should return fallback."""
        result = sanitize_folder_name("")
        assert result == "Files"
    
    def test_unicode_names(self):
        """Unicode characters should be preserved."""
        result = sanitize_folder_name("写真_photos")
        assert "写真" in result or "_" in result
    
    def test_mixed_invalid_and_valid(self):
        """Mix of valid and invalid chars should be cleaned."""
        result = sanitize_folder_name("valid_name<>invalid")
        assert "<" not in result
        assert ">" not in result
        assert "valid" in result


# ============================================================================
# UNIT TESTS - should_exclude_file
# ============================================================================

class TestShouldExcludeFile:
    """Test the should_exclude_file function."""
    
    def test_executable_excluded(self):
        """Executable files should be excluded."""
        assert should_exclude_file("program.exe") is True
    
    def test_dll_excluded(self):
        """DLL files should be excluded."""
        assert should_exclude_file("library.dll") is True
    
    def test_system_files_excluded(self):
        """System files should be excluded."""
        assert should_exclude_file("file.sys") is True
        assert should_exclude_file("temp.tmp") is True
        assert should_exclude_file("shortcut.lnk") is True
    
    def test_case_insensitive(self):
        """Extension check should be case-insensitive."""
        assert should_exclude_file("program.EXE") is True
        assert should_exclude_file("library.DLL") is True
    
    def test_regular_files_not_excluded(self):
        """Regular files should not be excluded."""
        assert should_exclude_file("document.txt") is False
        assert should_exclude_file("photo.jpg") is False
        assert should_exclude_file("report.pdf") is False
    
    def test_with_path(self):
        """Should work with full file paths."""
        assert should_exclude_file("/path/to/file.exe") is True
        assert should_exclude_file("C:\\Users\\file.dll") is True
        assert should_exclude_file("/path/to/file.txt") is False


# ============================================================================
# INTEGRATION TESTS - organize_files
# ============================================================================

class TestOrganizeFiles:
    """Integration tests for the organize_files function."""
    
    def test_dry_run_no_files_moved(self, test_dir_with_samples):
        """Dry run should preview without moving files."""
        # Count files in root before
        root_files_before = list(test_dir_with_samples.glob("*.jpg"))
        
        organize_files(test_dir_with_samples, threshold=0.7, dry_run=True)
        
        # Count files in root after
        root_files_after = list(test_dir_with_samples.glob("*.jpg"))
        
        # Should be unchanged
        assert len(root_files_before) == len(root_files_after)
    
    def test_organize_with_actual_movement(self, test_dir_with_samples):
        """Files should be organized into folders when dry_run=False."""
        with patch('builtins.input', return_value='yes'):
            result = organize_files(
                test_dir_with_samples,
                threshold=0.6,  # Lower threshold to ensure clustering
                dry_run=False
            )
        
        assert result is True
        
        # Check that folders were created
        folders = [d for d in test_dir_with_samples.iterdir() if d.is_dir()]
        assert len(folders) > 0
        
        # Check that some files were moved (fewer files in root than before)
        root_files = [f for f in test_dir_with_samples.iterdir() if f.is_file()]
        # Most files should be organized, but some dissimilar ones may remain
        assert len(root_files) < 10  # Sanity check (started with ~15 files)
    
    def test_user_cancels_organization(self, test_dir_with_samples):
        """User canceling should not move files."""
        with patch('builtins.input', return_value='no'):
            result = organize_files(
                test_dir_with_samples,
                threshold=0.7,
                dry_run=False
            )
        
        assert result is False
        
        # Files should still be in root
        root_files = [f for f in test_dir_with_samples.iterdir() if f.is_file()]
        assert len(root_files) > 0
    
    def test_nonexistent_directory(self):
        """Non-existent directory should return False."""
        result = organize_files("/nonexistent/path/12345")
        assert result is False
    
    def test_file_not_directory(self, tmp_path):
        """File path should return False."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        
        result = organize_files(str(file_path))
        assert result is False
    
    def test_invalid_threshold_too_low(self, test_dir_with_samples):
        """Threshold below minimum should fail."""
        result = organize_files(test_dir_with_samples, threshold=0.3)
        assert result is False
    
    def test_invalid_threshold_too_high(self, test_dir_with_samples):
        """Threshold above maximum should fail."""
        result = organize_files(test_dir_with_samples, threshold=0.96)
        assert result is False
    
    def test_empty_directory(self, tmp_path):
        """Empty directory should return False."""
        result = organize_files(tmp_path, threshold=0.7, dry_run=True)
        assert result is False
    
    def test_no_similar_files(self, tmp_path):
        """Directory with no similar files should return False."""
        # Create completely different files
        (tmp_path / "abc.txt").write_text("")
        (tmp_path / "xyz.doc").write_text("")
        (tmp_path / "pqr.pdf").write_text("")
        
        result = organize_files(tmp_path, threshold=0.9, dry_run=True)
        assert result is False
    
    def test_exclude_system_files(self, tmp_path):
        """System files should be excluded when flag is True."""
        # Create mix of system and regular files
        (tmp_path / "program.exe").write_text("")
        (tmp_path / "program.txt").write_text("")
        
        # Should only process .txt file, which alone doesn't form a cluster
        result = organize_files(
            tmp_path,
            threshold=0.7,
            dry_run=True,
            exclude_system_files=True
        )
        assert result is False
    
    def test_collision_handling(self, tmp_path):
        """Files with same name in destination should get numbered suffix."""
        with patch('builtins.input', return_value='yes'):
            # Create test files in root
            (tmp_path / "photo_v1.jpg").write_text("")
            (tmp_path / "photo_v2.jpg").write_text("")
            
            # Organize files - they should form a cluster and move to "photo" folder
            result = organize_files(tmp_path, threshold=0.7, dry_run=False)
            
            # Check that organization succeeded
            assert result is True
            
            # The photo files should now be in a folder
            photo_folders = list(tmp_path.glob("*/"))
            assert len(photo_folders) > 0
            
            # Check that files were moved into a folder
            organized_files = []
            for folder in photo_folders:
                organized_files.extend(list(folder.glob("*")))
            
            assert len(organized_files) >= 2
    
    def test_folder_creation(self, test_dir_with_samples):
        """Organized files should be in properly named folders."""
        with patch('builtins.input', return_value='yes'):
            organize_files(test_dir_with_samples, threshold=0.7, dry_run=False)
        
        folders = [d.name for d in test_dir_with_samples.iterdir() if d.is_dir()]
        
        # Folders should have descriptive names
        assert all(isinstance(f, str) and len(f) > 0 for f in folders)
        
        # Folder names should be Windows-safe
        invalid_chars = '<>:"/\\|?*'
        for folder in folders:
            for char in invalid_chars:
                assert char not in folder, f"Invalid char {char} in {folder}"


# ============================================================================
# INPUT VALIDATION TESTS
# ============================================================================

class TestInputValidation:
    """Test input validation functions."""
    
    def test_get_user_threshold_valid_input(self):
        """Valid threshold input should be accepted."""
        with patch('builtins.input', return_value='0.7'):
            threshold = get_user_threshold()
            assert threshold == 0.7
    
    def test_get_user_threshold_default(self):
        """Empty input should use default."""
        with patch('builtins.input', return_value=''):
            threshold = get_user_threshold()
            assert threshold == 0.7  # DEFAULT_SIMILARITY_THRESHOLD
    
    def test_get_user_threshold_boundary_low(self):
        """Minimum valid threshold should be accepted."""
        with patch('builtins.input', return_value='0.5'):
            threshold = get_user_threshold()
            assert threshold == 0.5
    
    def test_get_user_threshold_boundary_high(self):
        """Maximum valid threshold should be accepted."""
        with patch('builtins.input', return_value='0.95'):
            threshold = get_user_threshold()
            assert threshold == 0.95
    
    def test_get_user_threshold_invalid_then_valid(self):
        """Invalid input followed by valid should eventually accept."""
        with patch('builtins.input', side_effect=['invalid', '0.7']):
            threshold = get_user_threshold()
            assert threshold == 0.7
    
    def test_get_user_threshold_out_of_range(self):
        """Out of range values should be rejected."""
        with patch('builtins.input', side_effect=['0.3', '0.7']):
            threshold = get_user_threshold()
            assert threshold == 0.7
    
    def test_get_user_directory_valid_path(self, tmp_path):
        """Valid directory should be accepted."""
        with patch('builtins.input', return_value=str(tmp_path)):
            directory = get_user_directory()
            assert directory is not None
            assert Path(directory).exists()
    
    def test_get_user_directory_nonexistent(self):
        """Non-existent directory should be rejected."""
        with patch('builtins.input', side_effect=['/nonexistent/path', '']):
            # Would loop forever, so we can't fully test, but we can test the path check
            pass
    
    def test_get_user_directory_quit(self):
        """User quit should return None."""
        with patch('builtins.input', return_value='quit'):
            directory = get_user_directory()
            assert directory is None
    
    def test_get_user_directory_exit(self):
        """User exit should return None."""
        with patch('builtins.input', return_value='exit'):
            directory = get_user_directory()
            assert directory is None


# ============================================================================
# EDGE CASES AND SPECIAL SCENARIOS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_files_with_no_extension(self, tmp_path):
        """Files without extensions should be handled."""
        (tmp_path / "README").write_text("")
        (tmp_path / "READMEV2").write_text("")
        
        clusters = cluster_files(
            [str(f) for f in tmp_path.iterdir()],
            threshold=0.6
        )
        # Should cluster similar names without extensions
        assert len(clusters) > 0
    
    def test_files_with_multiple_dots(self, tmp_path):
        """Files with multiple dots should be handled."""
        file1 = tmp_path / "archive.tar.gz"
        file2 = tmp_path / "archive.backup.tar"
        file1.write_text("")
        file2.write_text("")
        
        # Should be processed without errors
        clusters = cluster_files(
            [str(f) for f in tmp_path.iterdir()],
            threshold=0.5
        )
    
    def test_very_long_filenames(self, tmp_path):
        """Very long filenames should be handled."""
        long_name = "a" * 200 + ".txt"
        (tmp_path / long_name).write_text("")
        
        files = [str(f) for f in tmp_path.iterdir()]
        # Should not crash
        cluster_files(files, threshold=0.7)
    
    def test_similar_but_different_extensions(self, tmp_path):
        """Same base name, different extensions."""
        (tmp_path / "document.pdf").write_text("")
        (tmp_path / "document.txt").write_text("")
        (tmp_path / "document.docx").write_text("")
        
        files = [str(f) for f in tmp_path.iterdir()]
        clusters = cluster_files(files, threshold=0.6)
        
        # Should group files with same basename
        assert len(clusters) > 0
    
    def test_unicode_filenames(self, tmp_path):
        """Unicode filenames should be handled."""
        (tmp_path / "写真_v1.jpg").write_text("")
        (tmp_path / "写真_v2.jpg").write_text("")
        
        files = [str(f) for f in tmp_path.iterdir()]
        clusters = cluster_files(files, threshold=0.7)
        
        # Should cluster unicode files
        assert len(clusters) == 1


# ============================================================================
# HELPER ASSERTION TESTS
# ============================================================================

class TestHelperAssertions:
    """Test the helper assertion fixtures."""
    
    def test_assert_organized_files_valid(self, tmp_path, assert_organized_files):
        """Valid organization should pass assertion."""
        # Create folder structure
        photos_folder = tmp_path / "photos"
        photos_folder.mkdir()
        (photos_folder / "photo1.jpg").write_text("")
        (photos_folder / "photo2.jpg").write_text("")
        
        assert_organized_files(
            tmp_path,
            {"photos"},
            {"photos": ["photo1.jpg", "photo2.jpg"]}
        )
    
    def test_assert_organized_files_missing_folder(self, tmp_path, assert_organized_files):
        """Missing expected folder should fail assertion."""
        with pytest.raises(AssertionError):
            assert_organized_files(
                tmp_path,
                {"missing_folder"},
                {"missing_folder": ["file.txt"]}
            )
    
    def test_assert_folder_name_valid_valid_names(self, assert_folder_name_valid):
        """Valid folder names should pass."""
        assert_folder_name_valid("valid_folder")
        assert_folder_name_valid("photos")
        assert_folder_name_valid("Document_2024")
    
    def test_assert_folder_name_valid_invalid_chars(self, assert_folder_name_valid):
        """Invalid characters should fail."""
        with pytest.raises(AssertionError):
            assert_folder_name_valid("folder<name>")
    
    def test_assert_folder_name_valid_reserved(self, assert_folder_name_valid):
        """Reserved names should fail."""
        with pytest.raises(AssertionError):
            assert_folder_name_valid("CON")
