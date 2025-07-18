"""
OperatorOS Spreadsheet to Power BI Transformer
Integrated module for transforming messy spreadsheets into clean data and Power BI configurations
"""
import os
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from werkzeug.utils import secure_filename

from processors.analyzer import SpreadsheetAnalyzer
from processors.cleaner import DataCleaner
from processors.powerbi_generator import PowerBIGenerator

class SpreadsheetTransformer:
    """Main transformer class that coordinates analysis, cleaning, and Power BI generation"""
    
    def __init__(self):
        self.upload_folder = Path('uploads')
        self.output_folder = Path('outputs')
        
        # Ensure directories exist
        self.upload_folder.mkdir(exist_ok=True)
        self.output_folder.mkdir(exist_ok=True)
        
        # Initialize processors
        self.analyzer = SpreadsheetAnalyzer()
        self.cleaner = DataCleaner()
        self.powerbi_generator = PowerBIGenerator()
        
        logging.info("SpreadsheetTransformer initialized")
    
    def transform_file(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """
        Main transformation method that processes a spreadsheet file
        
        Args:
            file_path: Path to the uploaded file
            original_filename: Original name of the uploaded file
            
        Returns:
            Dict containing transformation results and download paths
        """
        try:
            logging.info(f"Starting transformation of {original_filename}")
            
            # Step 1: Analyze spreadsheet structure
            logging.info("Analyzing spreadsheet structure...")
            analysis = self.analyzer.analyze(file_path)
            
            # Step 2: Clean and structure data
            logging.info("Cleaning and structuring data...")
            cleaned_data = self.cleaner.clean(file_path, analysis)
            
            # Step 3: Generate Power BI configuration
            logging.info("Generating Power BI configuration...")
            powerbi_config = self.powerbi_generator.generate(cleaned_data, analysis)
            
            # Step 4: Save outputs
            transformation_id = str(uuid.uuid4())[:8]
            excel_filename = f"cleaned_data_{transformation_id}.xlsx"
            config_filename = f"powerbi_config_{transformation_id}.json"
            
            excel_path = self.output_folder / excel_filename
            config_path = self.output_folder / config_filename
            
            # Save cleaned Excel file
            cleaned_data.to_excel(excel_path, index=False, sheet_name='Clean_Data')
            
            # Save Power BI configuration
            with open(config_path, 'w') as f:
                json.dump(powerbi_config, f, indent=2)
            
            logging.info(f"Transformation complete. ID: {transformation_id}")
            
            return {
                'success': True,
                'transformation_id': transformation_id,
                'analysis': analysis,
                'cleaned_data_info': {
                    'rows': len(cleaned_data),
                    'columns': list(cleaned_data.columns),
                    'file_path': str(excel_path),
                    'filename': excel_filename
                },
                'powerbi_config_info': {
                    'dashboards': powerbi_config['dashboards'],
                    'file_path': str(config_path),
                    'filename': config_filename
                },
                'downloads': {
                    'excel': f'/download/excel/{transformation_id}',
                    'config': f'/download/config/{transformation_id}'
                }
            }
            
        except Exception as e:
            logging.error(f"Error transforming {original_filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file type is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}
    
    def get_file_path(self, transformation_id: str, file_type: str) -> Optional[str]:
        """Get file path for download"""
        if file_type == 'excel':
            pattern = f"cleaned_data_{transformation_id}.xlsx"
        elif file_type == 'config':
            pattern = f"powerbi_config_{transformation_id}.json"
        else:
            return None
        
        file_path = self.output_folder / pattern
        return str(file_path) if file_path.exists() else None
    
    def save_uploaded_file(self, file) -> str:
        """Save uploaded file and return path"""
        if file.filename == '':
            raise ValueError("No file selected")
        
        if not self.allowed_file(file.filename):
            raise ValueError("Invalid file type. Only Excel (.xlsx, .xls) and CSV files are supported")
        
        filename = secure_filename(file.filename)
        timestamp = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{filename}"
        
        file_path = self.upload_folder / filename
        file.save(str(file_path))
        
        return str(file_path)
    
    def cleanup_old_files(self, days_old: int = 7):
        """Clean up old uploaded and output files"""
        import time
        import os
        
        current_time = time.time()
        day_in_seconds = 24 * 60 * 60
        cutoff_time = current_time - (days_old * day_in_seconds)
        
        # Clean uploads
        for file_path in self.upload_folder.glob('*'):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                logging.info(f"Cleaned up old upload: {file_path}")
        
        # Clean outputs
        for file_path in self.output_folder.glob('*'):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                logging.info(f"Cleaned up old output: {file_path}")