"""
OperatorOS EOS: Economic Operating System
Transforms any prompt into a profit-ready monetizable opportunity
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from models import db, Payment, PaymentStatus
from stripe_manager import StripeManager
from notifications import NotificationManager


class DeliveryMethod(Enum):
    """Available delivery methods for EOS offerings"""
    PDF_REPORT = "pdf_report"
    DIGITAL_GUIDE = "digital_guide"
    VIDEO_ANALYSIS = "video_analysis"
    CONSULTATION_CALL = "consultation_call"
    CUSTOM_TEMPLATE = "custom_template"
    AI_ANALYSIS = "ai_analysis"
    WORKFLOW_AUTOMATION = "workflow_automation"


@dataclass
class EOSOffering:
    """Data class for EOS-generated offerings"""
    title: str
    description: str
    value_proposition: str
    price: float
    delivery_method: DeliveryMethod
    fulfillment_time: str
    marketing_hook: str
    stripe_product_data: Dict[str, Any]
    agent_routing: Optional[str] = None
    tools_required: List[str] = None


class EOSSystem:
    """Economic Operating System - Transforms prompts into monetizable opportunities"""
    
    def __init__(self):
        self.stripe_manager = StripeManager()
        self.notification_manager = NotificationManager()
        self.csuite_manager = None  # Will be initialized later to avoid circular imports
        
    def transform_prompt(self, prompt: str, context: Dict[str, Any] = None) -> EOSOffering:
        """
        Transform any prompt into a soul-aligned monetizable offering
        
        Args:
            prompt: The input prompt to transform
            context: Optional context about user preferences, expertise, etc.
            
        Returns:
            EOSOffering: Complete monetization package
        """
        try:
            # Step 1: Soul-Aligned Translation
            offering_concept = self._generate_soul_aligned_concept(prompt, context)
            
            # Step 2: Ethical Pricing Structure
            pricing = self._calculate_ethical_pricing(offering_concept)
            
            # Step 3: Delivery Route Optimization
            delivery_method = self._optimize_delivery_route(offering_concept)
            
            # Step 4: Marketing Hook Creation
            marketing_hook = self._create_marketing_hook(offering_concept, pricing)
            
            # Step 5: Agent Routing Assessment
            agent_routing = self._assess_agent_routing(offering_concept, delivery_method)
            
            # Step 6: Stripe Product Data
            stripe_data = self._prepare_stripe_data(offering_concept, pricing)
            
            offering = EOSOffering(
                title=offering_concept['title'],
                description=offering_concept['description'],
                value_proposition=offering_concept['value_proposition'],
                price=pricing['amount'],
                delivery_method=delivery_method,
                fulfillment_time=pricing['fulfillment_time'],
                marketing_hook=marketing_hook,
                stripe_product_data=stripe_data,
                agent_routing=agent_routing,
                tools_required=offering_concept.get('tools_required', [])
            )
            
            logging.info(f"EOS transformed prompt into offering: {offering.title} - ${offering.price}")
            return offering
            
        except Exception as e:
            logging.error(f"Error transforming prompt in EOS: {str(e)}")
            raise
    
    def _generate_soul_aligned_concept(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate authentic offering concept aligned with capabilities"""
        
        # Analyze prompt for core value and opportunity
        if any(keyword in prompt.lower() for keyword in ['form', 'fitness', 'exercise', 'movement']):
            return {
                'title': 'AI Form Check Pro Report',
                'description': 'Professional movement analysis with personalized improvement recommendations',
                'value_proposition': 'Get expert-level form feedback in 5 minutes that usually takes weeks to develop',
                'category': 'fitness_analysis',
                'tools_required': ['video_analysis', 'ai_assessment', 'pdf_generation']
            }
            
        elif any(keyword in prompt.lower() for keyword in ['strategy', 'business', 'plan', 'growth']):
            return {
                'title': 'Strategic Intelligence Briefing',
                'description': 'C-Suite level strategic analysis and actionable recommendations',
                'value_proposition': 'Executive-grade strategic insights without the consulting fees',
                'category': 'business_strategy',
                'tools_required': ['csuite_agents', 'strategic_analysis', 'executive_report']
            }
            
        elif any(keyword in prompt.lower() for keyword in ['content', 'marketing', 'social', 'copy']):
            return {
                'title': 'High-Converting Content Package',
                'description': 'Platform-optimized content with psychological triggers for maximum engagement',
                'value_proposition': 'Content that converts browsers into buyers using proven psychology',
                'category': 'content_creation',
                'tools_required': ['ai_copywriting', 'psychology_analysis', 'platform_optimization']
            }
            
        elif any(keyword in prompt.lower() for keyword in ['automation', 'workflow', 'system', 'process']):
            return {
                'title': 'Workflow Automation Blueprint',
                'description': 'Custom automation strategy with step-by-step implementation guide',
                'value_proposition': 'Save 10+ hours per week with intelligent workflow automation',
                'category': 'automation_consulting',
                'tools_required': ['process_analysis', 'automation_design', 'implementation_guide']
            }
            
        else:
            # Generic intelligent analysis offering
            return {
                'title': 'AI-Powered Insight Report',
                'description': 'Deep analysis and actionable recommendations using advanced AI systems',
                'value_proposition': 'Professional-grade analysis that reveals hidden opportunities and solutions',
                'category': 'ai_analysis',
                'tools_required': ['multi_agent_analysis', 'insight_generation', 'report_creation']
            }
    
    def _calculate_ethical_pricing(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ethical pricing based on value and complexity"""
        
        base_prices = {
            'fitness_analysis': 15.99,
            'business_strategy': 29.99,
            'content_creation': 19.99,
            'automation_consulting': 24.99,
            'ai_analysis': 12.99
        }
        
        fulfillment_times = {
            'fitness_analysis': '5 minutes',
            'business_strategy': '15 minutes',
            'content_creation': '10 minutes',
            'automation_consulting': '20 minutes',
            'ai_analysis': '8 minutes'
        }
        
        category = concept.get('category', 'ai_analysis')
        
        return {
            'amount': base_prices.get(category, 12.99),
            'fulfillment_time': fulfillment_times.get(category, '10 minutes'),
            'value_multiplier': 10  # $15 for 5 minutes = $180/hour equivalent value
        }
    
    def _optimize_delivery_route(self, concept: Dict[str, Any]) -> DeliveryMethod:
        """Determine optimal delivery method based on offering type"""
        
        delivery_mapping = {
            'fitness_analysis': DeliveryMethod.VIDEO_ANALYSIS,
            'business_strategy': DeliveryMethod.PDF_REPORT,
            'content_creation': DeliveryMethod.DIGITAL_GUIDE,
            'automation_consulting': DeliveryMethod.WORKFLOW_AUTOMATION,
            'ai_analysis': DeliveryMethod.AI_ANALYSIS
        }
        
        category = concept.get('category', 'ai_analysis')
        return delivery_mapping.get(category, DeliveryMethod.PDF_REPORT)
    
    def _create_marketing_hook(self, concept: Dict[str, Any], pricing: Dict[str, Any]) -> str:
        """Create scroll-stopping marketing hook for social platforms"""
        
        hooks = {
            'fitness_analysis': f"🎯 Get professional form analysis in {pricing['fulfillment_time']} (normally takes weeks) → Perfect your technique → Avoid injuries → Maximize gains. AI-powered assessment for just ${pricing['amount']}. Upload video → Get expert feedback → Transform your training.",
            
            'business_strategy': f"💡 C-Suite level strategy session for ${pricing['amount']}? Yes, really. → Get executive insights → Identify growth opportunities → Receive actionable roadmap. What Fortune 500 CEOs pay $10k+ for, delivered in {pricing['fulfillment_time']}.",
            
            'content_creation': f"🔥 Content that actually converts for ${pricing['amount']} → Psychology-driven copy → Platform optimization → Engagement magnets. Stop posting into the void. Start creating content that turns followers into customers.",
            
            'automation_consulting': f"⚡ Save 10+ hours/week with smart automation → Custom workflow blueprint → Step-by-step implementation → ROI in first week. Transform chaos into systems for just ${pricing['amount']}.",
            
            'ai_analysis': f"🧠 Professional AI analysis in {pricing['fulfillment_time']} → Deep insights → Hidden opportunities → Actionable recommendations. What consultants charge hundreds for, delivered instantly for ${pricing['amount']}."
        }
        
        category = concept.get('category', 'ai_analysis')
        return hooks.get(category, hooks['ai_analysis'])
    
    def _assess_agent_routing(self, concept: Dict[str, Any], delivery_method: DeliveryMethod) -> Optional[str]:
        """Determine if agent routing is needed for complex fulfillment"""
        
        complex_categories = ['business_strategy', 'automation_consulting']
        
        if concept.get('category') in complex_categories:
            if concept.get('category') == 'business_strategy':
                return 'csuite_executive_briefing'
            elif concept.get('category') == 'automation_consulting':
                return 'operatoros_workflow_chain'
        
        return None
    
    def _initialize_csuite_manager(self):
        """Lazy initialization of CSuite manager to avoid circular imports"""
        if self.csuite_manager is None:
            try:
                from csuite_agents import CSuiteAgentManager
                self.csuite_manager = CSuiteAgentManager()
            except ImportError:
                logging.warning("CSuite agents not available for EOS routing")
                self.csuite_manager = None
    
    def _prepare_stripe_data(self, concept: Dict[str, Any], pricing: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Stripe product data for payment link creation"""
        
        return {
            'name': concept['title'],
            'description': concept['description'],
            'unit_amount': int(pricing['amount'] * 100),  # Convert to cents
            'currency': 'usd',
            'metadata': {
                'category': concept.get('category', 'ai_analysis'),
                'fulfillment_time': pricing['fulfillment_time'],
                'delivery_method': concept.get('category', 'ai_analysis'),
                'auto_fulfill': 'true'
            }
        }
    
    def create_instant_payment_link(self, offering: EOSOffering, client_email: str = None) -> Dict[str, Any]:
        """Create instant Stripe payment link for the offering"""
        try:
            # Use StripeManager to create payment link
            result = self.stripe_manager.create_payment_link(
                project_name=offering.title,
                client_name="EOS Customer",
                client_email=client_email or "customer@example.com",
                amount=offering.price,
                description=offering.description
            )
            
            if result.get('success'):
                # Add EOS-specific metadata
                result['eos_offering'] = {
                    'title': offering.title,
                    'fulfillment_time': offering.fulfillment_time,
                    'delivery_method': offering.delivery_method.value,
                    'marketing_hook': offering.marketing_hook,
                    'agent_routing': offering.agent_routing
                }
                
                # Send notification
                self.notification_manager.add_notification(
                    "EOS Payment Link Created",
                    f"New EOS offering ready: {offering.title} - ${offering.price}",
                    "success",
                    {"payment_url": result.get('payment_url')}
                )
            
            return result
            
        except Exception as e:
            logging.error(f"Error creating EOS payment link: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create payment link: {str(e)}"
            }
    
    def generate_deployment_package(self, offering: EOSOffering, payment_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete deployment package ready for immediate use"""
        
        return {
            "offering_summary": {
                "title": offering.title,
                "price": f"${offering.price}",
                "fulfillment_time": offering.fulfillment_time,
                "value_proposition": offering.value_proposition
            },
            "payment_link": payment_result.get('payment_url', ''),
            "marketing_content": {
                "hook": offering.marketing_hook,
                "platforms": ["Instagram", "TikTok", "Twitter", "Email"],
                "cta": f"Get instant access → {payment_result.get('payment_url', '')}"
            },
            "fulfillment_setup": {
                "delivery_method": offering.delivery_method.value,
                "agent_routing": offering.agent_routing,
                "tools_required": offering.tools_required,
                "automation_ready": True
            },
            "next_steps": [
                "Share marketing hook on social platforms",
                "Send payment link to interested prospects",
                "Monitor fulfillment automation",
                "Scale successful offerings"
            ],
            "created_at": datetime.utcnow().isoformat()
        }


# Global EOS instance
eos_system = EOSSystem()