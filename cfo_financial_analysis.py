"""
CFO Financial Analysis Module for OperatorOS
Comprehensive analysis of bank account data for digital nomad transition
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

class CFOFinancialAnalyzer:
    """
    Advanced financial analysis for CFO agent recommendations
    Analyzes spending patterns, nomad readiness, and optimization opportunities
    """
    
    def __init__(self):
        self.spending_data = None
        self.savings_data = None
        self.main_account_data = None
        self.analysis_results = {}
        
    def load_bank_data(self, spending_csv: str, savings_csv: str, main_csv: str) -> Dict[str, Any]:
        """Load and process bank account CSV data"""
        try:
            # Load all three account datasets
            self.spending_data = pd.read_csv(spending_csv)
            self.savings_data = pd.read_csv(savings_csv)
            self.main_account_data = pd.read_csv(main_csv)
            
            # Standardize data formats
            for df in [self.spending_data, self.savings_data, self.main_account_data]:
                df['Date'] = pd.to_datetime(df['Date'])
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
                
            return {"status": "success", "message": "Bank data loaded successfully"}
            
        except Exception as e:
            return {"status": "error", "message": f"Error loading data: {str(e)}"}
    
    def analyze_nomad_readiness(self) -> Dict[str, Any]:
        """Calculate comprehensive nomad readiness score and recommendations"""
        
        # Combine all account data for comprehensive analysis
        all_transactions = pd.concat([
            self.spending_data, 
            self.savings_data, 
            self.main_account_data
        ], ignore_index=True)
        
        # Filter recent 6 months for accurate patterns
        recent_date = all_transactions['Date'].max()
        six_months_ago = recent_date - timedelta(days=180)
        recent_data = all_transactions[all_transactions['Date'] >= six_months_ago]
        
        # Income Analysis
        income_transactions = recent_data[recent_data['Amount'] > 0]
        monthly_income = self._calculate_monthly_income(income_transactions)
        
        # Expense Analysis
        expense_transactions = recent_data[recent_data['Amount'] < 0]
        monthly_expenses = self._calculate_monthly_expenses(expense_transactions)
        expense_categories = self._categorize_expenses(expense_transactions)
        
        # Nomad Optimization Analysis
        nomad_optimizations = self._analyze_nomad_optimizations(expense_categories)
        
        # Financial Health Metrics
        financial_health = self._calculate_financial_health(monthly_income, monthly_expenses)
        
        # Generate Nomad Readiness Score
        readiness_score = self._calculate_nomad_readiness_score(
            financial_health, nomad_optimizations, monthly_income, monthly_expenses
        )
        
        return {
            "nomad_readiness_score": readiness_score,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "expense_categories": expense_categories,
            "nomad_optimizations": nomad_optimizations,
            "financial_health": financial_health,
            "cfo_recommendations": self._generate_cfo_recommendations(
                readiness_score, financial_health, nomad_optimizations
            )
        }
    
    def _calculate_monthly_income(self, income_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate detailed monthly income analysis"""
        
        # Primary income sources
        salary_income = income_data[
            income_data['Description'].str.contains('BOSTON CHILDREN', na=False)
        ]['Amount'].sum()
        
        interest_income = income_data[
            income_data['Description'].str.contains('Interest Paid', na=False)
        ]['Amount'].sum()
        
        tax_refunds = income_data[
            income_data['Description'].str.contains('TAX REF', na=False)
        ]['Amount'].sum()
        
        total_monthly_income = income_data['Amount'].sum() / 6  # 6-month average
        
        return {
            "total_monthly": total_monthly_income,
            "salary_monthly": salary_income / 6,
            "interest_monthly": interest_income / 6,
            "tax_refunds_total": tax_refunds,
            "stability_score": 9.5 if salary_income > 0 else 3.0  # Salary = high stability
        }
    
    def _calculate_monthly_expenses(self, expense_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate detailed monthly expense analysis"""
        
        total_monthly_expenses = abs(expense_data['Amount'].sum()) / 6
        
        # Essential vs Discretionary
        essential_keywords = ['CREDIT', 'AUTO', 'INSURANCE', 'EVERSOURCE', 'NGRID', 'ATT']
        discretionary_keywords = ['CASINO', 'CINEMA', 'RESTAURANT', 'DUNKIN', 'COFFEE']
        
        essential_expenses = expense_data[
            expense_data['Description'].str.contains('|'.join(essential_keywords), na=False, case=False)
        ]['Amount'].sum()
        
        discretionary_expenses = expense_data[
            expense_data['Description'].str.contains('|'.join(discretionary_keywords), na=False, case=False)
        ]['Amount'].sum()
        
        return {
            "total_monthly": total_monthly_expenses,
            "essential_monthly": abs(essential_expenses) / 6,
            "discretionary_monthly": abs(discretionary_expenses) / 6,
            "savings_potential": abs(discretionary_expenses) * 0.5 / 6  # 50% reduction potential
        }
    
    def _categorize_expenses(self, expense_data: pd.DataFrame) -> Dict[str, float]:
        """Categorize expenses for nomad optimization analysis"""
        
        categories = {
            "Housing_LocationDependent": 0,
            "Transportation_LocationDependent": 0,
            "Utilities_LocationDependent": 0,
            "Food_Optimizable": 0,
            "Entertainment_Optimizable": 0,
            "Credit_Fixed": 0,
            "Insurance_Fixed": 0,
            "Subscriptions_Portable": 0
        }
        
        # Location-dependent expenses (can be reduced/eliminated as nomad)
        utilities = expense_data[
            expense_data['Description'].str.contains('EVERSOURCE|NGRID', na=False, case=False)
        ]['Amount'].sum()
        categories["Utilities_LocationDependent"] = abs(utilities) / 6
        
        transportation = expense_data[
            expense_data['Description'].str.contains('E-ZPass|AUTO|TESLA', na=False, case=False)
        ]['Amount'].sum()
        categories["Transportation_LocationDependent"] = abs(transportation) / 6
        
        # Optimizable expenses
        food = expense_data[
            expense_data['Description'].str.contains('DUNKIN|MCDONALD|RESTAURANT|COFFEE', na=False, case=False)
        ]['Amount'].sum()
        categories["Food_Optimizable"] = abs(food) / 6
        
        entertainment = expense_data[
            expense_data['Description'].str.contains('CASINO|CINEMA', na=False, case=False)
        ]['Amount'].sum()
        categories["Entertainment_Optimizable"] = abs(entertainment) / 6
        
        # Fixed expenses
        credit_payments = expense_data[
            expense_data['Description'].str.contains('CREDIT|CHASE|CAPITAL ONE', na=False, case=False)
        ]['Amount'].sum()
        categories["Credit_Fixed"] = abs(credit_payments) / 6
        
        insurance = expense_data[
            expense_data['Description'].str.contains('INSURANCE', na=False, case=False)
        ]['Amount'].sum()
        categories["Insurance_Fixed"] = abs(insurance) / 6
        
        # Portable subscriptions
        subscriptions = expense_data[
            expense_data['Description'].str.contains('ATT|REPLIT|Rocket Money', na=False, case=False)
        ]['Amount'].sum()
        categories["Subscriptions_Portable"] = abs(subscriptions) / 6
        
        return categories
    
    def _analyze_nomad_optimizations(self, categories: Dict[str, float]) -> Dict[str, Any]:
        """Analyze potential nomad lifestyle optimizations"""
        
        # Calculate potential savings
        location_dependent_total = (
            categories["Utilities_LocationDependent"] + 
            categories["Transportation_LocationDependent"]
        )
        
        optimizable_total = (
            categories["Food_Optimizable"] + 
            categories["Entertainment_Optimizable"]
        )
        
        # Nomad optimization scenarios
        conservative_savings = location_dependent_total * 0.6 + optimizable_total * 0.3
        aggressive_savings = location_dependent_total * 0.8 + optimizable_total * 0.6
        
        return {
            "location_dependent_expenses": location_dependent_total,
            "optimizable_expenses": optimizable_total,
            "conservative_monthly_savings": conservative_savings,
            "aggressive_monthly_savings": aggressive_savings,
            "nomad_expense_reduction_potential": (conservative_savings + aggressive_savings) / 2,
            "optimization_score": min(10, (conservative_savings / 500) * 10)  # Score based on $500+ savings
        }
    
    def _calculate_financial_health(self, income: Dict[str, float], expenses: Dict[str, float]) -> Dict[str, Any]:
        """Calculate comprehensive financial health metrics"""
        
        monthly_net = income["total_monthly"] - expenses["total_monthly"]
        savings_rate = (monthly_net / income["total_monthly"]) * 100 if income["total_monthly"] > 0 else 0
        
        # Emergency fund calculation (based on current expenses)
        emergency_fund_target = expenses["essential_monthly"] * 6  # 6 months essential expenses
        current_savings = 5000  # From user input
        emergency_fund_ratio = (current_savings / emergency_fund_target) * 100
        
        # Debt-to-income ratio
        debt_payments = expenses["total_monthly"] * 0.3  # Estimate 30% for debt payments
        debt_to_income = (debt_payments / income["total_monthly"]) * 100
        
        return {
            "monthly_net_cash_flow": monthly_net,
            "savings_rate_percent": savings_rate,
            "emergency_fund_ratio": emergency_fund_ratio,
            "emergency_fund_target": emergency_fund_target,
            "debt_to_income_ratio": debt_to_income,
            "financial_stability_score": self._calculate_stability_score(
                savings_rate, emergency_fund_ratio, debt_to_income
            )
        }
    
    def _calculate_stability_score(self, savings_rate: float, emergency_ratio: float, debt_ratio: float) -> float:
        """Calculate overall financial stability score (0-10)"""
        
        # Weighted scoring
        savings_score = min(10, savings_rate / 2)  # 20% savings rate = 10 points
        emergency_score = min(10, emergency_ratio / 10)  # 100% emergency fund = 10 points  
        debt_score = max(0, 10 - (debt_ratio / 5))  # Lower debt ratio = higher score
        
        return round((savings_score * 0.4 + emergency_score * 0.4 + debt_score * 0.2), 1)
    
    def _calculate_nomad_readiness_score(
        self, 
        financial_health: Dict[str, Any], 
        optimizations: Dict[str, Any],
        income: Dict[str, float],
        expenses: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate comprehensive nomad readiness score"""
        
        # Scoring factors (0-10 each)
        income_stability = income["stability_score"]  # Salary income = high score
        expense_flexibility = optimizations["optimization_score"]
        financial_health_score = financial_health["financial_stability_score"]
        
        # Location independence factors
        location_dependency = (optimizations["location_dependent_expenses"] / expenses["total_monthly"]) * 10
        location_independence_score = max(0, 10 - location_dependency)
        
        # Overall readiness calculation
        overall_score = (
            income_stability * 0.3 +
            expense_flexibility * 0.25 +
            financial_health_score * 0.25 +
            location_independence_score * 0.2
        )
        
        # Readiness categories
        if overall_score >= 8:
            readiness_level = "Ready to Launch"
        elif overall_score >= 6:
            readiness_level = "Nearly Ready"
        elif overall_score >= 4:
            readiness_level = "Preparation Needed"
        else:
            readiness_level = "Not Ready"
        
        return {
            "overall_score": round(overall_score, 1),
            "readiness_level": readiness_level,
            "income_stability": income_stability,
            "expense_flexibility": expense_flexibility,
            "financial_health": financial_health_score,
            "location_independence": location_independence_score,
            "timeline_estimate_weeks": max(4, int((10 - overall_score) * 5))
        }
    
    def _generate_cfo_recommendations(
        self, 
        readiness: Dict[str, Any], 
        health: Dict[str, Any], 
        optimizations: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate specific CFO recommendations for nomad transition"""
        
        recommendations = []
        
        # Emergency Fund Recommendation
        if health["emergency_fund_ratio"] < 100:
            recommendations.append({
                "priority": "HIGH",
                "category": "Emergency Fund",
                "action": f"Build emergency fund to ${health['emergency_fund_target']:,.0f}",
                "current_gap": health['emergency_fund_target'] - 5000,
                "timeline": "2-3 months",
                "impact_score": 9
            })
        
        # Expense Optimization
        if optimizations["nomad_expense_reduction_potential"] > 200:
            recommendations.append({
                "priority": "MEDIUM", 
                "category": "Expense Optimization",
                "action": f"Reduce location-dependent expenses by ${optimizations['conservative_monthly_savings']:,.0f}/month",
                "current_savings_potential": optimizations["conservative_monthly_savings"],
                "timeline": "1-2 months",
                "impact_score": 7
            })
        
        # Income Diversification
        recommendations.append({
            "priority": "HIGH",
            "category": "Income Diversification", 
            "action": "Develop location-independent income streams",
            "target_amount": 7400,  # User's current salary
            "timeline": "3-6 months",
            "impact_score": 10
        })
        
        # Debt Management
        if health["debt_to_income_ratio"] > 25:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Debt Reduction",
                "action": "Accelerate debt payoff before nomad transition",
                "estimated_debt": 10000,  # User's debt amount
                "timeline": "4-6 months", 
                "impact_score": 6
            })
        
        return recommendations

def generate_cfo_intelligence_report(csv_files: List[str]) -> str:
    """Generate formatted report for OperatorOS CFO agent"""
    
    analyzer = CFOFinancialAnalyzer()
    
    # Load data
    load_result = analyzer.load_bank_data(csv_files[0], csv_files[1], csv_files[2])
    if load_result["status"] != "success":
        return f"Error: {load_result['message']}"
    
    # Perform analysis
    analysis = analyzer.analyze_nomad_readiness()
    
    # Format report for CFO agent
    report = f"""
🎯 CFO FINANCIAL INTELLIGENCE REPORT
Digital Nomad Transition Analysis

📊 NOMAD READINESS ASSESSMENT
Overall Score: {analysis['nomad_readiness_score']['overall_score']}/10
Readiness Level: {analysis['nomad_readiness_score']['readiness_level']}
Estimated Timeline: {analysis['nomad_readiness_score']['timeline_estimate_weeks']} weeks

💰 FINANCIAL POSITION
Monthly Income: ${analysis['monthly_income']['total_monthly']:,.2f}
Monthly Expenses: ${analysis['monthly_expenses']['total_monthly']:,.2f}
Net Cash Flow: ${analysis['financial_health']['monthly_net_cash_flow']:,.2f}
Savings Rate: {analysis['financial_health']['savings_rate_percent']:.1f}%

🎯 NOMAD OPTIMIZATION OPPORTUNITIES
Location-Dependent Expenses: ${analysis['nomad_optimizations']['location_dependent_expenses']:,.2f}/month
Potential Monthly Savings: ${analysis['nomad_optimizations']['conservative_monthly_savings']:,.2f}
Optimization Score: {analysis['nomad_optimizations']['optimization_score']:.1f}/10

🏆 CFO NRT RECOMMENDATIONS
"""
    
    for i, rec in enumerate(analysis['cfo_recommendations'], 1):
        report += f"""
{i}. {rec['category']} ({rec['priority']} Priority)
   Action: {rec['action']}
   Timeline: {rec['timeline']}
   Impact Score: {rec['impact_score']}/10
"""
    
    report += f"""
🎯 NEXT RIGHT THING (NRT) FOR CFO
Based on analysis, your highest-impact financial action is:
{analysis['cfo_recommendations'][0]['action']}

Implementation starts: Immediately
Expected completion: {analysis['cfo_recommendations'][0]['timeline']}
Impact on nomad goal: Critical foundation for transition

This analysis enables your OperatorOS CFO agent to provide data-driven financial intelligence for your digital nomad transition.
"""
    
    return report

# Example usage for OperatorOS integration
if __name__ == "__main__":
    csv_files = [
        'attached_assets/transactions (1)_1752183259188.csv',
        'attached_assets/transactions (2)_1752183259188.csv', 
        'attached_assets/transactions_1752183259188.csv'
    ]
    
    report = generate_cfo_intelligence_report(csv_files)
    print(report)