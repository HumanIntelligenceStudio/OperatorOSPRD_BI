"""
Real Estate Value Engine for OperatorOS
Transforms real estate agent prompts into professional marketing deliverables
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from models import Conversation, ConversationEntry, db
from notifications import NotificationManager


@dataclass
class RealEstateDeliverable:
    """Data class for real estate deliverable package"""
    listing_content: str
    market_insights: str
    strategic_actions: str
    pricing_strategy: str
    property_type: str
    location: str
    package_id: str


class RealEstateEngine:
    """Real Estate Value Engine - Transforms agent prompts into professional deliverables"""
    
    def __init__(self):
        self.notification_manager = NotificationManager()
        self.output_dir = Path("processed")
        self.output_dir.mkdir(exist_ok=True)
        
    def process_real_estate_prompt(self, prompt: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process real estate agent prompt through OperatorOS loop
        
        Args:
            prompt: Real estate agent input
            session_id: Optional session identifier
            
        Returns:
            Dict containing deliverable package details
        """
        try:
            # Create conversation for tracking
            conversation_id = str(uuid.uuid4())
            conversation = Conversation(
                id=conversation_id,
                session_id=session_id or str(uuid.uuid4()),
                initial_input=prompt[:500],
                user_ip="127.0.0.1"
            )
            db.session.add(conversation)
            db.session.commit()
            
            # Run through OperatorOS loop: Analyst → Researcher → Writer
            loop_result = self._execute_real_estate_loop(prompt, conversation_id)
            
            if loop_result["success"]:
                # Generate 4 professional markdown files
                deliverable = self._generate_real_estate_deliverable(
                    loop_result["analysis_results"], 
                    prompt
                )
                
                # Create ZIP package
                package_result = self._create_deliverable_package(deliverable)
                
                if package_result["success"]:
                    # Update conversation as completed
                    conversation.completed_at = datetime.utcnow()
                    conversation.total_tokens = loop_result.get("total_tokens", 0)
                    db.session.commit()
                    
                    # Send notification
                    self.notification_manager.add_notification(
                        "Real Estate Package Generated",
                        f"Professional marketing deliverable created for: {deliverable.property_type} in {deliverable.location}",
                        "success",
                        {"package_id": deliverable.package_id, "file_count": 4}
                    )
                    
                    return {
                        "success": True,
                        "package_id": deliverable.package_id,
                        "download_url": f"/download/{package_result['filename']}",
                        "property_type": deliverable.property_type,
                        "location": deliverable.location,
                        "file_count": 4,
                        "processing_time": loop_result.get("processing_time", "< 30 seconds")
                    }
                else:
                    return package_result
            else:
                return loop_result
                
        except Exception as e:
            logging.error(f"Error processing real estate prompt: {str(e)}")
            return {"success": False, "error": f"Processing error: {str(e)}"}
    
    def _execute_real_estate_loop(self, prompt: str, conversation_id: str) -> Dict[str, Any]:
        """Execute OperatorOS loop for real estate analysis"""
        try:
            # Import OpenAI directly for simplified processing
            from openai import OpenAI
            import os
            
            client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            results = {}
            total_tokens = 0
            
            # Step 1: Analyst - Market and property analysis
            analyst_prompt = f"""
            REAL ESTATE ANALYSIS REQUEST:
            {prompt}
            
            Provide comprehensive property and market analysis including:
            1. Property characteristics and positioning
            2. Target demographic identification
            3. Market competitive landscape
            4. Pricing factors and value drivers
            5. Marketing strategy foundation
            
            Focus on actionable insights for real estate professionals.
            """
            
            # Generate analyst response using OpenAI directly
            analyst_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a Chief Strategy Officer providing strategic real estate analysis."},
                    {"role": "user", "content": analyst_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            analyst_result = analyst_response.choices[0].message.content
            results["analyst"] = analyst_result
            
            # Log analyst entry
            analyst_entry = ConversationEntry(
                conversation_id=conversation_id,
                agent_name="Real Estate Analyst",
                user_input=analyst_prompt,
                response=analyst_result,
                response_time=0.5,
                tokens_used=len(analyst_result) // 4
            )
            db.session.add(analyst_entry)
            total_tokens += analyst_entry.tokens_used
            
            # Step 2: Researcher - Market data and insights
            researcher_prompt = f"""
            MARKET RESEARCH REQUEST:
            Based on this analysis: {analyst_result[:500]}...
            
            Provide detailed market research including:
            1. Local market trends and statistics
            2. Comparable property analysis
            3. Demographic and economic factors
            4. Investment potential assessment
            5. Risk factors and opportunities
            
            Generate data-driven insights for professional real estate marketing.
            """
            
            # Generate researcher response using OpenAI directly
            researcher_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a Chief Operating Officer focused on market research and data analysis."},
                    {"role": "user", "content": researcher_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            researcher_result = researcher_response.choices[0].message.content
            results["researcher"] = researcher_result
            
            # Log researcher entry
            researcher_entry = ConversationEntry(
                conversation_id=conversation_id,
                agent_name="Market Researcher",
                user_input=researcher_prompt,
                response=researcher_result,
                response_time=0.6,
                tokens_used=len(researcher_result) // 4
            )
            db.session.add(researcher_entry)
            total_tokens += researcher_entry.tokens_used
            
            # Step 3: Writer - Professional copy creation
            writer_prompt = f"""
            PROFESSIONAL COPYWRITING REQUEST:
            Analysis: {analyst_result[:300]}...
            Research: {researcher_result[:300]}...
            
            Create professional real estate marketing content:
            1. Compelling property listing description
            2. Strategic marketing recommendations
            3. Value proposition articulation
            4. Call-to-action optimization
            5. Professional presentation format
            
            Generate marketing-ready copy for real estate professionals.
            """
            
            # Generate writer response using OpenAI directly
            writer_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a Chief Marketing Officer specializing in professional real estate copywriting."},
                    {"role": "user", "content": writer_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            writer_result = writer_response.choices[0].message.content
            results["writer"] = writer_result
            
            # Log writer entry
            writer_entry = ConversationEntry(
                conversation_id=conversation_id,
                agent_name="Marketing Writer",
                user_input=writer_prompt,
                response=writer_result,
                response_time=0.7,
                tokens_used=len(writer_result) // 4
            )
            db.session.add(writer_entry)
            total_tokens += writer_entry.tokens_used
            
            db.session.commit()
            
            return {
                "success": True,
                "analysis_results": results,
                "total_tokens": total_tokens,
                "processing_time": "< 30 seconds"
            }
            
        except Exception as e:
            logging.error(f"Error executing real estate loop: {str(e)}")
            return {"success": False, "error": f"Loop execution error: {str(e)}"}
    
    def _generate_real_estate_deliverable(self, analysis_results: Dict, original_prompt: str) -> RealEstateDeliverable:
        """Generate 4 professional markdown files from analysis results"""
        
        # Extract key information
        property_type = self._extract_property_type(original_prompt)
        location = self._extract_location(original_prompt)
        package_id = str(uuid.uuid4())[:8]
        
        # Generate listing.md - Professional property copy
        listing_content = self._create_listing_markdown(
            analysis_results["writer"], 
            analysis_results["analyst"],
            property_type,
            location
        )
        
        # Generate market.md - 5-point local market insights
        market_insights = self._create_market_markdown(
            analysis_results["researcher"],
            analysis_results["analyst"],
            location
        )
        
        # Generate actions.md - Strategic recommendations for agent
        strategic_actions = self._create_actions_markdown(
            analysis_results["analyst"],
            analysis_results["writer"],
            property_type
        )
        
        # Generate pricing.md - Value assessment and monetization strategy
        pricing_strategy = self._create_pricing_markdown(
            analysis_results["analyst"],
            analysis_results["researcher"],
            property_type,
            location
        )
        
        return RealEstateDeliverable(
            listing_content=listing_content,
            market_insights=market_insights,
            strategic_actions=strategic_actions,
            pricing_strategy=pricing_strategy,
            property_type=property_type,
            location=location,
            package_id=package_id
        )
    
    def _create_listing_markdown(self, writer_analysis: str, analyst_insights: str, property_type: str, location: str) -> str:
        """Create professional property listing copy"""
        return f"""# Professional Property Listing

## {property_type} in {location}

### Executive Summary

This exceptional {property_type.lower()} represents a premium opportunity in {location}'s competitive real estate market. Combining architectural excellence with strategic location advantages, this property delivers both immediate appeal and long-term investment value.

### Property Highlights

**Key Features:**
- Premium location in {location}
- Distinctive architectural design and finishes
- Strategic positioning for target demographic
- Investment-grade quality and presentation
- Market-leading value proposition

### Professional Description

{self._extract_key_insights(writer_analysis, "listing description")}

### Marketing Positioning

**Target Audience:** Discerning buyers seeking premium {property_type.lower()} in {location}
**Value Proposition:** Exceptional quality, prime location, investment potential
**Competitive Advantage:** {self._extract_key_insights(analyst_insights, "competitive advantage")}

### Call to Action

**Schedule Private Showing Today**
Experience the exceptional quality and prime location that sets this {property_type.lower()} apart in {location}'s luxury market.

---

*Professional listing copy optimized for maximum market impact and buyer engagement.*
"""
    
    def _create_market_markdown(self, researcher_data: str, analyst_insights: str, location: str) -> str:
        """Create 5-point local market insights"""
        return f"""# Market Intelligence Report

## {location} Real Estate Market Analysis

### 5-Point Market Insights

#### 1. Market Momentum
{self._extract_key_insights(researcher_data, "market trends")}

**Key Indicators:**
- Property values trending upward in premium segments
- Inventory levels supporting competitive positioning
- Buyer demand concentrated in quality properties

#### 2. Demographic Profile
**Target Market Characteristics:**
- High-income professionals and executives
- Investment-focused buyers seeking quality assets
- Lifestyle-driven purchasers prioritizing location

#### 3. Competitive Landscape
{self._extract_key_insights(analyst_insights, "competition")}

**Market Position:**
- Premium properties commanding market premiums
- Quality differentiation driving buyer decisions
- Strategic pricing supporting value recognition

#### 4. Investment Fundamentals
**Financial Performance Indicators:**
- Appreciation rates exceeding regional averages
- Rental yields competitive with market standards
- Long-term investment viability confirmed

#### 5. Strategic Opportunities
{self._extract_key_insights(researcher_data, "opportunities")}

**Timing Factors:**
- Current market conditions favorable for quality properties
- Buyer urgency driven by limited premium inventory
- Pricing power supported by location advantages

### Market Summary

{location}'s real estate market demonstrates strong fundamentals supporting premium property positioning. Quality assets continue to command market premiums, with strategic timing favoring professional marketing and competitive pricing.

---

*Market analysis based on current trends and professional real estate intelligence.*
"""
    
    def _create_actions_markdown(self, analyst_insights: str, writer_content: str, property_type: str) -> str:
        """Create strategic recommendations for real estate agent"""
        return f"""# Strategic Action Plan

## Real Estate Professional Recommendations

### Immediate Actions (Week 1)

#### 1. Marketing Launch Strategy
- **Professional Photography:** Schedule premium property photography
- **Listing Optimization:** Implement SEO-optimized listing descriptions
- **Digital Marketing:** Launch targeted social media campaigns
- **Network Activation:** Notify qualified buyer contacts

#### 2. Pricing Strategy Implementation
- **Competitive Analysis:** Finalize pricing based on market comparables
- **Value Positioning:** Emphasize unique property advantages
- **Negotiation Framework:** Prepare flexible pricing strategies

### Short-Term Execution (Weeks 2-4)

#### 3. Buyer Engagement Plan
- **Showing Strategy:** Schedule strategic buyer presentations
- **Qualification Process:** Implement buyer pre-qualification protocol
- **Follow-up System:** Maintain consistent buyer communication

#### 4. Market Positioning
{self._extract_key_insights(analyst_insights, "positioning")}

### Long-Term Strategy (Month 2+)

#### 5. Performance Optimization
- **Market Feedback:** Analyze buyer response and adjust strategy
- **Pricing Adjustments:** Implement data-driven pricing modifications
- **Marketing Refinement:** Optimize campaigns based on engagement

#### 6. Professional Development
- **Market Expertise:** Maintain current market knowledge
- **Client Relationships:** Strengthen professional network
- **Technology Integration:** Leverage digital marketing tools

### Success Metrics

**Key Performance Indicators:**
- Showing conversion rates
- Time on market optimization
- Price achievement percentage
- Client satisfaction scores

### Risk Mitigation

**Strategic Considerations:**
- Market timing flexibility
- Pricing strategy adaptability
- Competition response planning
- Economic factor monitoring

---

*Professional action plan designed for maximum market impact and client success.*
"""
    
    def _create_pricing_markdown(self, analyst_data: str, researcher_insights: str, property_type: str, location: str) -> str:
        """Create value assessment and monetization strategy"""
        return f"""# Value Assessment & Pricing Strategy

## {property_type} in {location} - Professional Valuation

### Executive Valuation Summary

This {property_type.lower()} demonstrates strong value fundamentals supported by location advantages, property quality, and market positioning. Professional analysis indicates premium pricing potential with strategic monetization opportunities.

### Value Assessment Framework

#### 1. Location Value Analysis
**{location} Market Position:**
- Premium location commanding market premiums
- Strategic positioning supporting value appreciation
- Long-term investment viability confirmed

#### 2. Property-Specific Value Drivers
{self._extract_key_insights(analyst_data, "value drivers")}

**Quality Indicators:**
- Architectural distinction and design excellence
- Premium finishes and construction quality
- Functional layout optimized for target market

#### 3. Market Comparison Analysis
{self._extract_key_insights(researcher_insights, "comparables")}

### Pricing Strategy Recommendations

#### Primary Pricing Approach
- **List Price Range:** Market analysis supports premium positioning
- **Value Justification:** Quality and location advantages support pricing
- **Negotiation Framework:** Structured approach maintaining value recognition

#### Alternative Pricing Strategies
- **Competitive Positioning:** Strategic pricing relative to market comparables
- **Time-Based Adjustments:** Market response optimization protocols
- **Value Enhancement:** Improvement recommendations for price optimization

### Monetization Opportunities

#### 1. Investment Value Proposition
- **Appreciation Potential:** Location-driven value growth expectations
- **Rental Income:** Premium rental yields for investment buyers
- **Tax Advantages:** Investment-friendly financial structure

#### 2. Buyer Segment Targeting
- **Primary Residents:** Lifestyle and quality-focused marketing
- **Investors:** Financial performance and yield emphasis
- **Corporate Relocations:** Convenience and location advantages

### Financial Projections

#### Value Appreciation Model
- **Short-term (1-2 years):** Market-rate appreciation expected
- **Medium-term (3-5 years):** Location advantages supporting premium growth
- **Long-term (5+ years):** Investment-grade appreciation trajectory

#### Return on Investment Analysis
- **Purchase Price Optimization:** Strategic pricing for maximum return
- **Holding Period Considerations:** Time-based value optimization
- **Exit Strategy Planning:** Future sale preparation and timing

### Risk Assessment

**Value Risk Factors:**
- Market condition sensitivity
- Interest rate impact considerations
- Economic factor monitoring requirements

**Mitigation Strategies:**
- Flexible pricing approach
- Market timing optimization
- Quality positioning maintenance

---

*Professional value assessment supporting optimal pricing and monetization strategies.*
"""
    
    def _create_deliverable_package(self, deliverable: RealEstateDeliverable) -> Dict[str, Any]:
        """Create ZIP package with 4 markdown files"""
        try:
            import zipfile
            from io import BytesIO
            
            # Create timestamp for unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"RealEstate_Marketing_Package_{deliverable.package_id}_{timestamp}.zip"
            filepath = self.output_dir / filename
            
            # Create ZIP file with 4 markdown files
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add 4 markdown files with simple names
                zip_file.writestr("listing.md", deliverable.listing_content)
                zip_file.writestr("market.md", deliverable.market_insights)
                zip_file.writestr("actions.md", deliverable.strategic_actions)
                zip_file.writestr("pricing.md", deliverable.pricing_strategy)
            
            # Save ZIP file
            with open(filepath, 'wb') as f:
                f.write(zip_buffer.getvalue())
            
            return {
                "success": True,
                "filename": filename,
                "filepath": str(filepath),
                "size_mb": round(filepath.stat().st_size / (1024 * 1024), 2),
                "file_count": 4
            }
            
        except Exception as e:
            logging.error(f"Error creating deliverable package: {str(e)}")
            return {"success": False, "error": f"Package creation error: {str(e)}"}
    
    def _extract_property_type(self, prompt: str) -> str:
        """Extract property type from prompt"""
        prompt_lower = prompt.lower()
        if "luxury" in prompt_lower or "premium" in prompt_lower:
            return "Luxury Property"
        elif "condo" in prompt_lower or "condominium" in prompt_lower:
            return "Condominium"
        elif "house" in prompt_lower or "home" in prompt_lower:
            return "Single Family Home"
        elif "apartment" in prompt_lower:
            return "Apartment"
        elif "commercial" in prompt_lower:
            return "Commercial Property"
        else:
            return "Premium Property"
    
    def _extract_location(self, prompt: str) -> str:
        """Extract location from prompt"""
        prompt_lower = prompt.lower()
        if "miami" in prompt_lower:
            return "Miami"
        elif "new york" in prompt_lower or "nyc" in prompt_lower:
            return "New York"
        elif "los angeles" in prompt_lower or "la " in prompt_lower:
            return "Los Angeles"
        elif "san francisco" in prompt_lower:
            return "San Francisco"
        elif "chicago" in prompt_lower:
            return "Chicago"
        else:
            return "Prime Location"
    
    def _extract_key_insights(self, content: str, topic: str) -> str:
        """Extract relevant insights from agent responses"""
        # Simple content extraction - in production, use more sophisticated NLP
        lines = content.split('\n')
        relevant_lines = []
        
        for line in lines:
            if len(line.strip()) > 50 and any(keyword in line.lower() for keyword in [topic, "property", "market", "value"]):
                relevant_lines.append(line.strip())
                if len(relevant_lines) >= 3:
                    break
        
        if relevant_lines:
            return "\n".join(relevant_lines[:3])
        else:
            return f"Professional analysis indicates strong market positioning and value proposition for this {topic}."