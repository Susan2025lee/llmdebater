"""
Unit tests for the file_handler module
"""
import os
import tempfile
import pytest
from src.utils.file_handler import (
    read_text_file,
    validate_file_type,
    list_files_in_directory
)

class TestFileHandler:
    """Test cases for file_handler functions"""
    
    def setup_method(self):
        """Setup test environment before each test"""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create sample text files
        self.text_file_path = os.path.join(self.temp_dir.name, "sample.txt")
        self.markdown_file_path = os.path.join(self.temp_dir.name, "sample.md")
        self.json_file_path = os.path.join(self.temp_dir.name, "sample.json")
        
        with open(self.text_file_path, 'w', encoding='utf-8') as f:
            f.write("This is a sample text file for testing.")
        
        with open(self.markdown_file_path, 'w', encoding='utf-8') as f:
            f.write("# Sample Markdown\nThis is a sample markdown file for testing.")
        
        with open(self.json_file_path, 'w', encoding='utf-8') as f:
            f.write('{"key": "value"}')
    
    def teardown_method(self):
        """Cleanup test environment after each test"""
        # Cleanup temporary directory
        self.temp_dir.cleanup()
    
    def test_read_text_file(self):
        """Test reading a text file"""
        # Test reading a text file
        content = read_text_file(self.text_file_path)
        assert content == "This is a sample text file for testing."
        
        # Test reading a markdown file
        content = read_text_file(self.markdown_file_path)
        assert content == "# Sample Markdown\nThis is a sample markdown file for testing."
    
    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist"""
        nonexistent_file = os.path.join(self.temp_dir.name, "nonexistent.txt")
        with pytest.raises(FileNotFoundError):
            read_text_file(nonexistent_file)
    
    def test_read_directory(self):
        """Test reading a directory instead of a file"""
        with pytest.raises(ValueError):
            read_text_file(self.temp_dir.name)
    
    def test_validate_file_type(self):
        """Test validating file types"""
        # Test validating a text file
        assert validate_file_type(self.text_file_path) == True
        
        # Test validating a markdown file
        assert validate_file_type(self.markdown_file_path) == True
        
        # Test validating a file with extension not in allowed list
        assert validate_file_type(self.json_file_path) == False
        
        # Test validating with custom allowed extensions
        assert validate_file_type(self.json_file_path, ['.json']) == True
    
    def test_list_files_in_directory(self):
        """Test listing files in a directory"""
        # Test listing all files
        files = list_files_in_directory(self.temp_dir.name)
        assert len(files) == 3
        
        # Test listing files with specific extensions
        text_files = list_files_in_directory(self.temp_dir.name, ['.txt'])
        assert len(text_files) == 1
        assert any(file.endswith('.txt') for file in text_files)
        
        # Test listing markdown and text files
        text_and_md_files = list_files_in_directory(self.temp_dir.name, ['.txt', '.md'])
        assert len(text_and_md_files) == 2
        
    def test_list_nonexistent_directory(self):
        """Test listing files in a directory that doesn't exist"""
        nonexistent_dir = os.path.join(self.temp_dir.name, "nonexistent")
        with pytest.raises(FileNotFoundError):
            list_files_in_directory(nonexistent_dir)
    
    def test_list_file_as_directory(self):
        """Test listing a file as a directory"""
        with pytest.raises(NotADirectoryError):
            list_files_in_directory(self.text_file_path) 