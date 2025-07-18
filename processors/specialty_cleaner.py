"""
Specialty-focused data cleaner for 52 healthcare specialties
Preserves all specialty data while organizing for patient self-service analysis
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

class SpecialtyCleaner:
    def clean_specialty_data(self, filepath: str, analysis: Dict[str, Any]) -> pd.DataFrame:
        """Clean specialty data while preserving all 52 specialties"""
        
        # Read with proper structure
        df = pd.read_excel(filepath, header=None)
        
        # Create structured dataframe
        specialty_data = []
        
        # Column mapping based on analysis
        column_mapping = {
            0: 'Specialty_Name',
            1: 'Lead_Person', 
            3: 'Auto_Scheduler_Dept',
            4: 'Auto_Scheduler_PLP',
            5: 'Fast_Pass_Status',
            6: 'Ticket_Scheduling_Amb',
            7: 'Ticket_Scheduling_FollowUp',
            8: 'Open_Direct_Scheduling',
            9: 'Open_Scheduling',
            10: 'Direct_Scheduling',
            11: 'Outlook_Integration',
            14: 'Fast_Pass_Notes',
            15: 'Ticket_Scheduling_Notes',
            16: 'Build_Notes',
            17: 'Build_Status_Questions',
            18: 'PRD_DEP_Specialty'
        }
        
        # Extract all 52 specialties (rows 3-54)
        for i in range(3, 55):
            if i < len(df) and pd.notna(df.iloc[i, 0]):
                row_data = {}
                for col_idx, col_name in column_mapping.items():
                    if col_idx < len(df.columns):
                        row_data[col_name] = df.iloc[i, col_idx]
                    else:
                        row_data[col_name] = None
                
                # Add calculated fields
                row_data['Row_Number'] = i
                row_data['Patient_Self_Service_Score'] = self._calculate_pss_score(row_data)
                row_data['Readiness_Category'] = self._categorize_readiness(row_data['Patient_Self_Service_Score'])
                row_data['Priority_Level'] = self._assign_priority(row_data)
                
                specialty_data.append(row_data)
        
        # Create clean DataFrame
        clean_df = pd.DataFrame(specialty_data)
        
        # Add metadata columns
        clean_df['Record_ID'] = range(1, len(clean_df) + 1)
        clean_df['Analysis_Date'] = pd.Timestamp.now()
        clean_df['Dashboard_Focus'] = 'Patient Self Service Features'
        
        return clean_df
    
    def _calculate_pss_score(self, row_data: Dict) -> int:
        """Calculate Patient Self Service score"""
        score = 0
        
        # Fast Pass (25 points)
        fast_pass = str(row_data.get('Fast_Pass_Status', '')).upper()
        if 'A' in fast_pass or 'LIVE' in fast_pass:
            score += 25
        elif 'M' in fast_pass:
            score += 12
        elif 'PROGRESS' in fast_pass:
            score += 5
        
        # Ticket Scheduling Auto (20 points)
        ticket_auto = str(row_data.get('Ticket_Scheduling_Amb', '')).upper()
        if ticket_auto == 'A':
            score += 20
        elif ticket_auto == 'M':
            score += 8
        elif 'M/A' in ticket_auto:
            score += 15
        
        # Follow-up Scheduling (20 points) 
        followup = str(row_data.get('Ticket_Scheduling_FollowUp', '')).upper()
        if followup == 'A':
            score += 20
        elif followup == 'M':
            score += 8
        elif 'M/A' in followup:
            score += 15
        
        # Open/Direct Scheduling (20 points)
        open_sched = str(row_data.get('Open_Scheduling', '')).upper()
        direct_sched = str(row_data.get('Direct_Scheduling', '')).upper()
        if 'RAA' in open_sched or 'A' in direct_sched:
            score += 20
        elif 'M' in open_sched or 'M' in direct_sched:
            score += 10
        
        # Auto-scheduler Templates (15 points)
        auto_dept = str(row_data.get('Auto_Scheduler_Dept', '')).upper()
        auto_plp = str(row_data.get('Auto_Scheduler_PLP', '')).upper()
        if auto_dept or auto_plp:
            score += 15
        
        return min(score, 100)  # Cap at 100%
    
    def _categorize_readiness(self, score: int) -> str:
        """Categorize readiness based on score"""
        if score >= 85:
            return 'Fully Ready'
        elif score >= 70:
            return 'Mostly Ready'
        elif score >= 50:
            return 'In Progress'
        elif score >= 25:
            return 'Early Stage'
        else:
            return 'Needs Attention'
    
    def _assign_priority(self, row_data: Dict) -> str:
        """Assign priority based on current implementation status"""
        score = row_data.get('Patient_Self_Service_Score', 0)
        
        # High priority: Low scores (need attention)
        if score < 30:
            return 'High Priority'
        # Medium priority: Middle scores (in progress)
        elif score < 70:
            return 'Medium Priority'  
        # Low priority: High scores (mostly complete)
        else:
            return 'Low Priority'