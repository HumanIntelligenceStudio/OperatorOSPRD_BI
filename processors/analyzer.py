"""
Spreadsheet Analysis Module for OperatorOS
Analyzes spreadsheet structure and identifies patterns for transformation
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any

class SpreadsheetAnalyzer:
    def analyze(self, filepath: str) -> Dict[str, Any]:
        """Analyze spreadsheet structure and identify issues"""
        
        # Read file with no headers to analyze structure
        df_raw = pd.read_excel(filepath, header=None)
        
        analysis = {
            'total_rows': len(df_raw),
            'total_columns': len(df_raw.columns),
            'issues': [],
            'patterns': {},
            'recommendations': []
        }
        
        # Detect header row
        header_row = self._detect_header_row(df_raw)
        analysis['header_row'] = header_row
        
        # Detect merged cells
        merged_cells = self._detect_merged_cells(df_raw)
        if merged_cells:
            analysis['issues'].append({
                'type': 'merged_cells',
                'locations': merged_cells
            })
        
        # Detect color patterns (this would need cell styling info)
        analysis['patterns']['data_types'] = self._analyze_data_types(df_raw)
        
        # Detect Epic build patterns
        epic_patterns = self._detect_epic_patterns(df_raw)
        if epic_patterns:
            analysis['patterns']['epic_build'] = epic_patterns
            analysis['recommendations'].append('Epic Build Dashboard')
        
        # Detect workflow patterns
        if self._has_workflow_columns(df_raw):
            analysis['patterns']['workflow'] = True
            analysis['recommendations'].append('Workflow Tracking Dashboard')
        
        # Detect department patterns
        if self._has_department_columns(df_raw):
            analysis['patterns']['departments'] = True
            analysis['recommendations'].append('Department Readiness Dashboard')
        
        return analysis
    
    def _detect_header_row(self, df: pd.DataFrame) -> int:
        """Detect which row contains headers"""
        for idx, row in df.iterrows():
            non_null_count = row.notna().sum()
            if non_null_count > len(df.columns) * 0.7:  # 70% non-null threshold
                # Check if next row has different pattern
                if idx < len(df) - 1:
                    next_row = df.iloc[idx + 1]
                    if self._is_data_row(next_row):
                        return idx
        return 0
    
    def _detect_merged_cells(self, df: pd.DataFrame) -> List[Dict]:
        """Detect potential merged cells based on patterns"""
        merged = []
        
        # Look for rows with single value followed by empty cells
        for idx, row in df.iterrows():
            values = row.dropna()
            if len(values) == 1 and row.notna().sum() < len(row) / 2:
                merged.append({
                    'row': idx,
                    'type': 'horizontal_merge',
                    'value': values.iloc[0]
                })
        
        return merged
    
    def _analyze_data_types(self, df: pd.DataFrame) -> Dict[int, str]:
        """Analyze data types in each column"""
        types = {}
        for col in df.columns:
            col_data = df[col].dropna()
            if len(col_data) == 0:
                types[col] = 'empty'
            elif col_data.apply(lambda x: isinstance(x, (int, float))).all():
                types[col] = 'numeric'
            elif pd.to_datetime(col_data, errors='coerce').notna().all():
                types[col] = 'date'
            else:
                types[col] = 'text'
        return types
    
    def _detect_epic_patterns(self, df: pd.DataFrame) -> bool:
        """Detect if this is Epic build related data"""
        epic_keywords = ['module', 'workflow', 'build', 'epic', 'deployment']
        
        # Check all cells for Epic-related keywords
        all_text = df.astype(str).values.flatten()
        text_lower = ' '.join(all_text).lower()
        
        return any(keyword in text_lower for keyword in epic_keywords)
    
    def _has_workflow_columns(self, df: pd.DataFrame) -> bool:
        """Check for workflow-related columns"""
        workflow_keywords = ['status', 'approval', 'approved', 'pending', 'stage']
        all_text = df.astype(str).values.flatten()
        text_lower = ' '.join(all_text).lower()
        return any(keyword in text_lower for keyword in workflow_keywords)
    
    def _has_department_columns(self, df: pd.DataFrame) -> bool:
        """Check for department-related columns"""
        dept_keywords = ['department', 'team', 'owner', 'division', 'unit']
        all_text = df.astype(str).values.flatten()
        text_lower = ' '.join(all_text).lower()
        return any(keyword in text_lower for keyword in dept_keywords)
    
    def _is_data_row(self, row: pd.Series) -> bool:
        """Check if row contains actual data vs headers"""
        non_null = row.notna().sum()
        return non_null > 0 and non_null < len(row) * 0.9