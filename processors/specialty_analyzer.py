"""
Specialty-focused analyzer for healthcare scheduling optimization
Designed for 52 specialty analysis with patient self-service focus
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List

class SpecialtyAnalyzer:
    def analyze(self, filepath: str) -> Dict[str, Any]:
        """Analyze 52 specialties with focus on patient self-service features"""
        
        df = pd.read_excel(filepath, header=None)
        
        # Extract specialty data (rows 3-54)
        specialty_rows = []
        for i in range(3, 55):
            if i < len(df) and pd.notna(df.iloc[i, 0]):
                specialty_rows.append(i)
        
        analysis = {
            'total_specialties': len(specialty_rows),
            'specialty_rows': specialty_rows,
            'key_features': {
                'autosearch_templates': [3, 4],  # Auto-scheduler columns
                'online_scheduling': [8, 9, 10],  # Open, Direct scheduling
                'ticket_scheduling': [6, 7],     # Manual vs Auto ticket
                'fast_pass': [5],                # Fast Pass
                'request_appointment': [9]       # RAA functionality
            },
            'status_codes': {
                'A': 'Automatic Ticket Scheduling',
                'M': 'Manual Ticket Scheduling', 
                'RAA': 'Request an Appointment',
                'M/A': 'Mixed Manual/Automatic'
            },
            'color_coding': {
                'yellow': 'Opportunity to improve',
                'green': 'Satisfactory and functional',
                'red': 'Concerns / Not On',
                'light_green': 'On, but additional opportunity',
                'purple': 'In Progress'
            },
            'priority_focus': 'Patient Self Service (Fast Pass, Open, Direct, Ticket)',
            'dashboard_type': 'Specialty drill-down by feature implementation'
        }
        
        # Analyze each specialty's current status
        specialty_analysis = []
        for row in specialty_rows:
            specialty_name = df.iloc[row, 0]
            lead = df.iloc[row, 1]
            
            # Check key feature implementation
            features = {}
            features['fast_pass'] = df.iloc[row, 5] if row < len(df) else None
            features['ticket_auto'] = df.iloc[row, 6] if row < len(df) else None
            features['ticket_followup'] = df.iloc[row, 7] if row < len(df) else None
            features['open_scheduling'] = df.iloc[row, 8] if row < len(df) else None
            features['direct_scheduling'] = df.iloc[row, 10] if row < len(df) else None
            
            # Calculate readiness score
            readiness_score = self._calculate_readiness(features)
            
            specialty_analysis.append({
                'row': row,
                'specialty': specialty_name,
                'lead': lead,
                'features': features,
                'readiness_score': readiness_score,
                'patient_self_service_ready': readiness_score >= 70
            })
        
        analysis['specialty_details'] = specialty_analysis
        return analysis
    
    def _calculate_readiness(self, features: Dict) -> int:
        """Calculate specialty readiness score based on patient self-service features"""
        score = 0
        total_possible = 0
        
        # Fast Pass implementation (30 points)
        if pd.notna(features.get('fast_pass')):
            if features['fast_pass'] in ['A', 'Live', 'On']:
                score += 30
            elif features['fast_pass'] in ['M', 'Manual']:
                score += 15
            elif features['fast_pass'] in ['In Progress', 'Purple']:
                score += 5
        total_possible += 30
        
        # Ticket Scheduling (25 points)
        if pd.notna(features.get('ticket_auto')):
            if features['ticket_auto'] == 'A':
                score += 25
            elif features['ticket_auto'] == 'M':
                score += 10
            elif features['ticket_auto'] == 'M/A':
                score += 18
        total_possible += 25
        
        # Open/Direct Scheduling (25 points)
        open_direct_score = 0
        if pd.notna(features.get('open_scheduling')):
            if features['open_scheduling'] in ['RAA', 'A']:
                open_direct_score += 15
        if pd.notna(features.get('direct_scheduling')):
            if features['direct_scheduling'] in ['A', 'On']:
                open_direct_score += 10
        score += min(open_direct_score, 25)
        total_possible += 25
        
        # Follow-up automation (20 points)
        if pd.notna(features.get('ticket_followup')):
            if features['ticket_followup'] == 'A':
                score += 20
            elif features['ticket_followup'] == 'M':
                score += 8
            elif features['ticket_followup'] == 'M/A':
                score += 14
        total_possible += 20
        
        return int((score / total_possible) * 100) if total_possible > 0 else 0