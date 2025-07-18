"""
Power BI Configuration Generator for OperatorOS
Generates Power BI dashboard configurations based on cleaned data patterns
"""
import pandas as pd
import json
from typing import Dict, List, Any

class PowerBIGenerator:
    def generate(self, df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Power BI configuration based on cleaned data"""
        
        config = {
            "dataSource": self._generate_datasource_config(),
            "dataModel": self._generate_datamodel(df),
            "dashboards": self._generate_dashboards(df, analysis),
            "theme": self._generate_theme(),
            "refreshSettings": {
                "schedule": "Daily",
                "time": "06:00",
                "timezone": "UTC"
            }
        }
        
        return config
    
    def _generate_datasource_config(self) -> Dict[str, Any]:
        """Generate data source configuration"""
        return {
            "type": "Excel",
            "connectionString": "Provider=Microsoft.ACE.OLEDB.12.0;Data Source={filepath};Extended Properties='Excel 12.0 Xml;HDR=YES';",
            "authentication": "Anonymous",
            "privacy": "Organizational"
        }
    
    def _generate_datamodel(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate data model configuration"""
        
        # Identify columns and types
        columns = []
        for col in df.columns:
            col_type = str(df[col].dtype)
            
            if 'int' in col_type:
                powerbi_type = "Int64"
            elif 'float' in col_type:
                powerbi_type = "Double"
            elif 'datetime' in col_type:
                powerbi_type = "DateTime"
            elif 'bool' in col_type:
                powerbi_type = "Boolean"
            else:
                powerbi_type = "Text"
            
            columns.append({
                "name": col,
                "dataType": powerbi_type,
                "formatString": self._get_format_string(col, powerbi_type)
            })
        
        # Generate measures
        measures = self._generate_measures(df)
        
        return {
            "tables": [{
                "name": "MainData",
                "columns": columns,
                "measures": measures
            }],
            "relationships": [],  # Would be populated if multiple tables
            "roles": []
        }
    
    def _generate_dashboards(self, df: pd.DataFrame, analysis: Dict[str, Any]) -> List[Dict]:
        """Generate dashboard configurations based on data patterns"""
        
        dashboards = []
        
        # Always create overview dashboard
        dashboards.append(self._create_overview_dashboard(df))
        
        # Create specific dashboards based on patterns
        if analysis['patterns'].get('epic_build'):
            dashboards.append(self._create_epic_dashboard(df))
        
        if analysis['patterns'].get('workflow'):
            dashboards.append(self._create_workflow_dashboard(df))
        
        if analysis['patterns'].get('departments'):
            dashboards.append(self._create_department_dashboard(df))
        
        return dashboards
    
    def _create_overview_dashboard(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create overview dashboard configuration"""
        
        visuals = []
        
        # KPI Cards
        kpi_metrics = ['Total_Records', 'Completion_Rate', 'Active_Items', 'Blocked_Items']
        for i, metric in enumerate(kpi_metrics):
            if self._can_calculate_metric(df, metric):
                visuals.append({
                    "type": "card",
                    "name": f"{metric}_Card",
                    "title": metric.replace('_', ' '),
                    "position": {
                        "x": i * 300,
                        "y": 0,
                        "width": 280,
                        "height": 100
                    },
                    "dataBindings": {
                        "values": [{
                            "measure": metric
                        }]
                    }
                })
        
        # Status distribution pie chart
        if 'Status' in df.columns or 'Status_Category' in df.columns:
            visuals.append({
                "type": "pieChart",
                "name": "Status_Distribution",
                "title": "Status Distribution",
                "position": {
                    "x": 0,
                    "y": 120,
                    "width": 600,
                    "height": 400
                },
                "dataBindings": {
                    "category": "Status_Category",
                    "values": [{
                        "measure": "Count_of_Records"
                    }]
                }
            })
        
        # Trend line if date columns exist
        date_cols = [col for col in df.columns if 'datetime' in str(df[col].dtype)]
        if date_cols:
            visuals.append({
                "type": "lineChart",
                "name": "Completion_Trend",
                "title": "Completion Trend",
                "position": {
                    "x": 620,
                    "y": 120,
                    "width": 600,
                    "height": 400
                },
                "dataBindings": {
                    "axis": date_cols[0],
                    "values": [{
                        "measure": "Cumulative_Completion"
                    }],
                    "legend": "Status_Category"
                }
            })
        
        return {
            "name": "Executive Overview",
            "displayName": "Executive Overview",
            "pages": [{
                "name": "Summary",
                "displayName": "Summary",
                "visuals": visuals
            }]
        }
    
    def _create_epic_dashboard(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create Epic-specific dashboard"""
        
        visuals = []
        
        # Module status matrix
        if 'Module' in df.columns:
            visuals.append({
                "type": "matrix",
                "name": "Module_Status_Matrix",
                "title": "Module Status Overview",
                "position": {
                    "x": 0,
                    "y": 0,
                    "width": 800,
                    "height": 500
                },
                "dataBindings": {
                    "rows": ["Module"],
                    "columns": ["Status_Category"],
                    "values": [{
                        "measure": "Count_of_Records"
                    }]
                }
            })
        
        # Timeline visual
        visuals.append({
            "type": "ganttChart",
            "name": "Build_Timeline",
            "title": "Build Timeline",
            "position": {
                "x": 0,
                "y": 520,
                "width": 1200,
                "height": 400
            },
            "dataBindings": {
                "task": "Module",
                "start": "Start_Date",
                "end": "End_Date",
                "progress": "Completion_Percentage"
            }
        })
        
        return {
            "name": "Epic Build Tracker",
            "displayName": "Epic Build Tracker",
            "pages": [{
                "name": "Build_Status",
                "displayName": "Build Status",
                "visuals": visuals
            }]
        }
    
    def _create_workflow_dashboard(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create workflow tracking dashboard"""
        
        visuals = []
        
        # Workflow funnel
        visuals.append({
            "type": "funnelChart",
            "name": "Workflow_Funnel",
            "title": "Workflow Stages",
            "position": {
                "x": 0,
                "y": 0,
                "width": 600,
                "height": 500
            },
            "dataBindings": {
                "category": "Workflow_Stage",
                "values": [{
                    "measure": "Count_of_Records"
                }]
            }
        })
        
        # Time in status
        if 'Days_In_Status' in df.columns:
            visuals.append({
                "type": "columnChart",
                "name": "Time_In_Status",
                "title": "Average Days in Status",
                "position": {
                    "x": 620,
                    "y": 0,
                    "width": 600,
                    "height": 500
                },
                "dataBindings": {
                    "axis": "Status_Category",
                    "values": [{
                        "measure": "Average_Days_In_Status"
                    }]
                }
            })
        
        return {
            "name": "Workflow Analytics",
            "displayName": "Workflow Analytics",
            "pages": [{
                "name": "Workflow_Overview",
                "displayName": "Workflow Overview",
                "visuals": visuals
            }]
        }
    
    def _create_department_dashboard(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create department readiness dashboard"""
        
        visuals = []
        
        # Department heatmap
        if 'Department' in df.columns:
            visuals.append({
                "type": "heatmap",
                "name": "Department_Readiness",
                "title": "Department Readiness Heatmap",
                "position": {
                    "x": 0,
                    "y": 0,
                    "width": 800,
                    "height": 600
                },
                "dataBindings": {
                    "rows": ["Department"],
                    "columns": ["Module"],
                    "values": [{
                        "measure": "Readiness_Score"
                    }],
                    "colorScale": {
                        "min": 0,
                        "mid": 50,
                        "max": 100,
                        "minColor": "#FF0000",
                        "midColor": "#FFFF00",
                        "maxColor": "#00FF00"
                    }
                }
            })
        
        return {
            "name": "Department Readiness",
            "displayName": "Department Readiness",
            "pages": [{
                "name": "Readiness_Overview",
                "displayName": "Readiness Overview",
                "visuals": visuals
            }]
        }
    
    def _generate_measures(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate DAX measures based on available columns"""
        
        measures = []
        
        # Basic count measure
        measures.append({
            "name": "Count_of_Records",
            "expression": "COUNTROWS(MainData)",
            "formatString": "#,##0"
        })
        
        # Total records
        measures.append({
            "name": "Total_Records",
            "expression": "COUNTROWS(MainData)",
            "formatString": "#,##0"
        })
        
        # Status-based measures
        if 'Status_Category' in df.columns:
            measures.append({
                "name": "Completion_Rate",
                "expression": "DIVIDE(CALCULATE(COUNTROWS(MainData), MainData[Status_Category] = \"Complete\"), COUNTROWS(MainData))",
                "formatString": "0.0%"
            })
            
            measures.append({
                "name": "Active_Items",
                "expression": "CALCULATE(COUNTROWS(MainData), MainData[Status_Category] = \"In Progress\")",
                "formatString": "#,##0"
            })
            
            measures.append({
                "name": "Blocked_Items",
                "expression": "CALCULATE(COUNTROWS(MainData), MainData[Status_Category] = \"Blocked\")",
                "formatString": "#,##0"
            })
        
        # Date-based measures
        if 'Days_In_Status' in df.columns:
            measures.append({
                "name": "Average_Days_In_Status",
                "expression": "AVERAGE(MainData[Days_In_Status])",
                "formatString": "#,##0.0"
            })
        
        # Completion percentage
        if 'Completion_Percentage' in df.columns:
            measures.append({
                "name": "Average_Completion",
                "expression": "AVERAGE(MainData[Completion_Percentage])",
                "formatString": "0.0%"
            })
        
        return measures
    
    def _generate_theme(self) -> Dict[str, Any]:
        """Generate Power BI theme configuration"""
        return {
            "name": "OperatorOS Theme",
            "dataColors": [
                "#28a745",  # Success green
                "#dc3545",  # Danger red
                "#ffc107",  # Warning yellow
                "#17a2b8",  # Info blue
                "#6c757d",  # Secondary gray
                "#343a40",  # Dark
                "#f8f9fa",  # Light
                "#007bff"   # Primary blue
            ],
            "background": "#FFFFFF",
            "foreground": "#252423",
            "tableAccent": "#28a745"
        }
    
    def _get_format_string(self, column: str, data_type: str) -> str:
        """Get appropriate format string for column"""
        
        column_lower = column.lower()
        
        # Currency formatting
        if any(word in column_lower for word in ['amount', 'price', 'cost', 'revenue']):
            return "$#,##0.00"
        
        # Percentage formatting
        if any(word in column_lower for word in ['percentage', 'percent', 'rate']):
            return "0.0%"
        
        # Date formatting
        if data_type == "DateTime":
            return "yyyy-MM-dd"
        
        # Number formatting
        if data_type in ["Int64", "Double"]:
            return "#,##0"
        
        return "General"
    
    def _can_calculate_metric(self, df: pd.DataFrame, metric: str) -> bool:
        """Check if a metric can be calculated from available columns"""
        
        if metric == "Total_Records":
            return True
        
        if metric == "Completion_Rate":
            return 'Status_Category' in df.columns
        
        if metric == "Active_Items":
            return 'Status_Category' in df.columns
        
        if metric == "Blocked_Items":
            return 'Status_Category' in df.columns
        
        return False