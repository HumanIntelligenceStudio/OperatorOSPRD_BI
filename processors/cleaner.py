"""
Data Cleaning Module for OperatorOS
Cleans and structures spreadsheet data for analysis
"""
import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List

class DataCleaner:
    def clean(self, filepath: str, analysis: Dict[str, Any]) -> pd.DataFrame:
        """Clean and restructure the spreadsheet data"""
        
        # Read with detected header row
        df = pd.read_excel(filepath, header=analysis['header_row'])
        
        # Clean column names
        df.columns = [self._clean_column_name(col) for col in df.columns]
        
        # Remove empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Handle merged cells from analysis
        if analysis['issues'] and any(issue['type'] == 'merged_cells' for issue in analysis['issues']):
            merged_locations = next(issue['locations'] for issue in analysis['issues'] if issue['type'] == 'merged_cells')
            df = self._handle_merged_cells(df, merged_locations)
        
        # Add metadata columns based on patterns
        if analysis['patterns'].get('epic_build'):
            df = self._add_epic_metadata(df)
        
        if analysis['patterns'].get('workflow'):
            df = self._add_workflow_metadata(df)
        
        # Standardize data types
        df = self._standardize_types(df)
        
        # Add calculated columns
        df = self._add_calculated_columns(df, analysis)
        
        return df
    
    def _clean_column_name(self, name: str) -> str:
        """Clean column names for consistency"""
        if pd.isna(name):
            return 'Unnamed'
        
        # Convert to string and clean
        name = str(name)
        name = re.sub(r'[^\w\s]', '', name)  # Remove special chars
        name = name.strip().replace(' ', '_')
        name = re.sub(r'_+', '_', name)  # Remove multiple underscores
        
        return name or 'Column'
    
    def _handle_merged_cells(self, df: pd.DataFrame, merged_locations: List[Dict]) -> pd.DataFrame:
        """Handle merged cells by creating group columns"""
        
        if not merged_locations:
            return df
        
        # Add group column for merged cells
        df['Group'] = ''
        current_group = None
        
        for idx, row in df.iterrows():
            # Check if this row is a merged cell indicator
            for merged in merged_locations:
                if merged['row'] == idx:
                    current_group = merged['value']
                    break
            
            if current_group and pd.notna(row).sum() > 1:  # Data row
                df.at[idx, 'Group'] = current_group
        
        # Remove rows that were just merged cell headers
        df = df[df['Group'] != '']
        
        return df
    
    def _add_epic_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Epic-specific metadata columns"""
        
        # Add status interpretation
        if 'Status' in df.columns:
            df['Status_Category'] = df['Status'].apply(self._categorize_status)
        
        # Add completion percentage if not present
        if 'Completion' not in df.columns and 'Status' in df.columns:
            df['Completion_Percentage'] = df['Status'].apply(self._estimate_completion)
        
        # Add priority scoring
        df['Priority_Score'] = self._calculate_priority(df)
        
        return df
    
    def _add_workflow_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add workflow-specific metadata"""
        
        # Add days in current status
        if 'Status_Date' in df.columns:
            df['Status_Date'] = pd.to_datetime(df['Status_Date'])
            df['Days_In_Status'] = (pd.Timestamp.now() - df['Status_Date']).dt.days
        
        # Add workflow stage
        if 'Status' in df.columns:
            df['Workflow_Stage'] = df['Status'].apply(self._determine_workflow_stage)
        
        return df
    
    def _standardize_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize data types across columns"""
        
        for col in df.columns:
            # Try to convert to numeric
            if df[col].dtype == 'object':
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass
            
            # Try to convert to datetime
            if col.lower() in ['date', 'created', 'updated', 'modified']:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass
        
        return df
    
    def _add_calculated_columns(self, df: pd.DataFrame, analysis: Dict) -> pd.DataFrame:
        """Add calculated columns based on data patterns"""
        
        # Add unique ID if not present
        if 'ID' not in df.columns and 'Id' not in df.columns:
            df['Record_ID'] = range(1, len(df) + 1)
        
        # Add date-based calculations
        date_cols = [col for col in df.columns if df[col].dtype == 'datetime64[ns]']
        if len(date_cols) >= 2:
            df['Duration_Days'] = (df[date_cols[-1]] - df[date_cols[0]]).dt.days
        
        return df
    
    def _categorize_status(self, status: str) -> str:
        """Categorize status values"""
        if pd.isna(status):
            return 'Unknown'
        
        status_lower = str(status).lower()
        
        if any(word in status_lower for word in ['complete', 'done', 'finished']):
            return 'Complete'
        elif any(word in status_lower for word in ['progress', 'working', 'active']):
            return 'In Progress'
        elif any(word in status_lower for word in ['blocked', 'issue', 'problem']):
            return 'Blocked'
        elif any(word in status_lower for word in ['pending', 'waiting', 'review']):
            return 'Pending'
        else:
            return 'Not Started'
    
    def _estimate_completion(self, status: str) -> int:
        """Estimate completion percentage from status"""
        category = self._categorize_status(status)
        
        completion_map = {
            'Complete': 100,
            'In Progress': 50,
            'Blocked': 25,
            'Pending': 75,
            'Not Started': 0,
            'Unknown': 0
        }
        
        return completion_map.get(category, 0)
    
    def _calculate_priority(self, df: pd.DataFrame) -> pd.Series:
        """Calculate priority score based on available data"""
        priority = pd.Series(50, index=df.index)  # Default priority
        
        # Increase priority for blocked items
        if 'Status' in df.columns:
            blocked_mask = df['Status'].str.contains('block', case=False, na=False)
            priority[blocked_mask] = 90
        
        # Adjust based on dates if available
        if 'Due_Date' in df.columns:
            try:
                days_until_due = (pd.to_datetime(df['Due_Date']) - pd.Timestamp.now()).dt.days
                priority[days_until_due < 7] = 85
                priority[days_until_due < 0] = 95
            except:
                pass
        
        return priority
    
    def _determine_workflow_stage(self, status: str) -> str:
        """Determine workflow stage from status"""
        if pd.isna(status):
            return 'Unknown'
        
        status_lower = str(status).lower()
        
        if 'initial' in status_lower or 'start' in status_lower:
            return 'Initiation'
        elif 'plan' in status_lower or 'design' in status_lower:
            return 'Planning'
        elif 'develop' in status_lower or 'build' in status_lower:
            return 'Execution'
        elif 'test' in status_lower or 'review' in status_lower:
            return 'Review'
        elif 'approve' in status_lower or 'sign' in status_lower:
            return 'Approval'
        elif 'complete' in status_lower or 'done' in status_lower:
            return 'Closure'
        else:
            return 'In Process'