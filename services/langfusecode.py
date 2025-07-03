# services/llm_analysis_service.py - CoT analysis for ALL input types with Langfuse tracing
from flask import Flask, request, jsonify
from langchain_community.llms import Ollama
from sentence_transformers import SentenceTransformer
from langfusecode import get_client
from langfuse.langchain import CallbackHandler
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Initialize Langfuse client for comprehensive tracing
langfuse = get_client()

class UniversalCoTAnalysisService:
    def __init__(self, model_name="llama3.1:8b"):
        self.llm = Ollama(model=model_name, temperature=0.1)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.db_service_url = "http://localhost:5001"
    
    def get_universal_cot_prompt(self, content, metadata):
        """Optimized, concise CoT prompt for any input format"""
        return f"""You are a senior DevOps engineer. Analyze the following content using Chain-of-Thought (CoT) reasoning. The content may be logs, text, JSON, YAML, or any format.

METADATA:
Tool: {metadata.get('tool', 'unknown')}
Project: {metadata.get('project', 'unknown')}
Environment: {metadata.get('environment', 'unknown')}
Log Type: {metadata.get('log_type', 'unknown')}
Status: {metadata.get('status', 'unknown')}

CONTENT:
{content}

Follow these steps:
1. Identify the content type and main purpose.
2. Extract key events, errors, warnings, and success indicators.
3. Diagnose root cause(s) of any issues.
4. Assess severity and business impact.
5. Recommend specific fixes and preventive actions.

Respond with a clear, structured analysis covering all steps. Be concise but thorough. Use bullet points or short paragraphs for each step.
"""
    
    def analyze_with_universal_cot(self, content, metadata):
        """Universal CoT analysis that works with ANY input format"""
        # Start top-level span for this analysis
        with langfuse.start_as_current_span(name="universal-cot-analysis") as span:
            span.update_trace(
                input={
                    "content": content,
                    "metadata": metadata,
                    "content_length": len(content),
                    "tool": metadata.get('tool', 'unknown'),
                    "log_type": metadata.get('log_type', 'unknown')
                },
                user_id="system",
                session_id=f"cot-{metadata.get('log_id', 'unknown')}"
            )

            try:
                start_time = datetime.now()
                print(f"🧠 Starting universal CoT analysis for {metadata.get('tool', 'unknown')} {metadata.get('log_type', 'unknown')} (any format)")
                
                # Generate universal CoT prompt
                prompt = self.get_universal_cot_prompt(content, metadata)
                
                # Get LLM response with CoT reasoning (with Langfuse tracing)
                with langfuse.start_as_current_span(name="cot-llm-invoke") as llm_span:
                    llm_span.update_trace(
                        input={"prompt": prompt, "prompt_length": len(prompt)},
                        metadata={"model": "llama3.1:8b", "temperature": 0.1}
                    )
                    handler = llm_span.get_langchain_handler()
                    llm_response = self.llm.invoke(prompt, config={"callbacks": [handler]})
                    llm_span.update_trace(output={"llm_response": llm_response, "response_length": len(llm_response)})

                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                print(f"📝 Received universal CoT response ({len(llm_response)} chars) in {processing_time:.0f}ms")
                
                # Extract structured insights using CoT principles
                with langfuse.start_as_current_span(name="cot-structured-extraction") as extract_span:
                    structured_analysis = self.extract_structured_insights_with_cot(llm_response, content, metadata)
                    structured_analysis['processing_time_ms'] = processing_time
                    structured_analysis['llm_response'] = llm_response
                    structured_analysis['analysis_method'] = 'Universal Chain-of-Thought reasoning'
                    extract_span.update_trace(output={"structured_analysis": structured_analysis})

                # After CoT analysis, check for similar errors
                with langfuse.start_as_current_span(name="similar-error-search") as search_span:
                    error_text = ''
                    if 'error' in content.lower():
                        error_lines = [line for line in content.splitlines() if 'error' in line.lower()]
                        error_text = error_lines[0] if error_lines else content[:200]
                    else:
                        error_text = content[:200]
                    
                    search_span.update_trace(input={"error_text": error_text})
                    similar_errors = self.find_similar_errors(error_text, metadata)
                    structured_analysis['similar_error_insights'] = {
                        'count': len(similar_errors),
                        'examples': similar_errors[:3]
                    }
                    search_span.update_trace(output={"similar_errors_found": len(similar_errors)})

                # Update root span with final analysis
                span.update_trace(output={"final_analysis": structured_analysis, "processing_time_ms": processing_time})
                print(f"✅ Universal CoT analysis completed for {metadata.get('tool', 'unknown')} {metadata.get('log_type', 'unknown')}")
                return structured_analysis
                
            except Exception as e:
                print(f"❌ Universal CoT analysis failed: {e}")
                span.update_trace(output={"error": str(e), "emergency_analysis": True})
                return self.create_cot_emergency_analysis(metadata, str(e))
    
    def extract_structured_insights_with_cot(self, llm_response, original_content, metadata):
        """Extract structured insights using CoT reasoning from any response format"""
        extraction_prompt = f"""Using Chain-of-Thought reasoning, extract structured information from this analysis:

ORIGINAL ANALYSIS:
{llm_response}

ORIGINAL CONTENT CONTEXT:
{original_content[:500]}...

METADATA:
- Tool: {metadata.get('tool', 'unknown')}
- Environment: {metadata.get('environment', 'unknown')}
- Log Type: {metadata.get('log_type', 'unknown')}

CHAIN-OF-THOUGHT EXTRACTION:

Step 1: Identify the main findings from the analysis
Step 2: Extract specific technical details and metrics
Step 3: Determine severity and impact levels
Step 4: Extract actionable recommendations
Step 5: Assess confidence and complexity

Based on this reasoning, provide the following information:
EXECUTIVE_SUMMARY: [brief summary of the log and the problem]
ROOT_CAUSE: [primary technical cause with confidence %]
FIX_STRATEGY: [specific actionable steps]
ROLLBACK_PLAN: [safe rollback procedures]
AUTO_FIX_FEASIBILITY: [can this be automated safely?]
SEVERITY_LEVEL: [low/medium/high/critical]
CONFIDENCE_SCORE: [0.0-1.0]
Confidence reasoning: [brief reasoning for confidence score]
ERROR_COUNT: [number of errors found]
WARNING_COUNT: [number of warnings found]
SUCCESS_INDICATORS: [number of success markers]
RESOLUTION_TIME: [estimated time to resolve]
BUSINESS_IMPACT: [0.0-1.0 scale]
BUSINESS_IMPACT_REASONING: [brief reasoning for business impact score]
TECHNICAL_COMPLEXITY: [low/medium/high]
MONITORING_RECOMMENDATIONS: [specific monitoring advice]
"""
        
        try:
            with langfuse.start_as_current_span(name="cot-extraction-llm-invoke") as extract_span:
                extract_span.update_trace(
                    input={"extraction_prompt": extraction_prompt, "prompt_length": len(extraction_prompt)}
                )
                handler = extract_span.get_langchain_handler()
                structured_response = self.llm.invoke(extraction_prompt, config={"callbacks": [handler]})
                extract_span.update_trace(
                    output={"structured_response": structured_response, "response_length": len(structured_response)}
                )
            return self.parse_cot_structured_response(structured_response, llm_response, original_content, metadata)
        except Exception as e:
            print(f"⚠️ CoT structured extraction failed: {e}")
            return self.pattern_based_cot_analysis(llm_response, original_content, metadata)
    
    def parse_cot_structured_response(self, structured_response, original_response, original_content, metadata):
        """Parse CoT structured response into final analysis"""
        def extract_cot_field(pattern, default=""):
            match = re.search(f"{pattern}:\s*(.+?)(?=\n[A-Z_]+:|$)", structured_response, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else default
        
        def extract_cot_numeric(pattern, default=0):
            try:
                text = extract_cot_field(pattern, str(default))
                numbers = re.findall(r'\d+\.?\d*', text)
                return float(numbers[0]) if numbers else default
            except:
                return default
        
        auto_fix_text = extract_cot_field("AUTO_FIX_FEASIBILITY", "Manual intervention required")
        auto_fix = "Manual intervention required"
        if any(word in auto_fix_text.lower() for word in ["yes", "safe", "automated", "can be automated"]):
            auto_fix = f"Automated fix possible: {auto_fix_text[:100]}"
        
        return {
            "failure_summary": extract_cot_field("EXECUTIVE_SUMMARY", f"CoT analysis of {metadata.get('tool', 'unknown')} {metadata.get('log_type', 'unknown')} content"),
            "root_cause": extract_cot_field("ROOT_CAUSE", "CoT analysis identified technical factors"),
            "fix_suggestion": extract_cot_field("FIX_STRATEGY", f"Apply {metadata.get('tool', 'unknown')} best practices"),
            "rollback_plan": extract_cot_field("ROLLBACK_PLAN", f"Standard {metadata.get('tool', 'unknown')} rollback procedures"),
            "auto_fix": auto_fix,
            "severity_level": extract_cot_field("SEVERITY_LEVEL", "medium").lower(),
            "confidence_score": min(max(extract_cot_numeric("CONFIDENCE_SCORE", 0.8), 0.0), 1.0),
            "confidence_reasoning": extract_cot_field("Confidence reasoning", "CoT analysis applied with confidence"),
            "error_count": int(extract_cot_numeric("ERROR_COUNT", 0)),
            "warning_count": int(extract_cot_numeric("WARNING_COUNT", 0)),
            "success_indicators": int(extract_cot_numeric("SUCCESS_INDICATORS", 0)),
            "resolution_time_estimate": extract_cot_field("RESOLUTION_TIME", "2-4 hours"),
            "business_impact_score": min(max(extract_cot_numeric("BUSINESS_IMPACT", 0.5), 0.0), 1.0),
            "business_impact_reasoning": extract_cot_field("BUSINESS_IMPACT_REASONING", "CoT analysis applied with business impact assessment"),
            "technical_complexity": extract_cot_field("TECHNICAL_COMPLEXITY", "medium").lower(),
            "failure_category": f"{metadata.get('log_type', 'general')}_cot_analysis",
            "affected_components": [metadata.get('tool', 'unknown')],
            "build_duration_seconds": 0,
            "test_pass_rate": 0.0,
            "deployment_success": metadata.get('status') == 'success',
            "monitoring_recommendations": extract_cot_field("MONITORING_RECOMMENDATIONS", f"Monitor {metadata.get('tool', 'unknown')} operations"),
            "full_synthesis": original_response,
            "cot_reasoning_applied": True,
            "input_format": "universal",
            "processing_method": "universal_cot"
        }
    
    def pattern_based_cot_analysis(self, llm_response, original_content, metadata):
        """Pattern-based CoT analysis when structured extraction fails"""
        with langfuse.start_as_current_span(name="pattern-based-cot-analysis") as pattern_span:
            pattern_span.update_trace(
                input={"llm_response_length": len(llm_response), "content_length": len(original_content)}
            )
            
            print("🔄 Applying pattern-based CoT analysis...")
            error_count = len(re.findall(r'(?:error|Error|ERROR|failed|Failed|FAILED)', original_content, re.IGNORECASE))
            warning_count = len(re.findall(r'(?:warning|Warning|WARNING|warn|Warn)', original_content, re.IGNORECASE))
            success_indicators = len(re.findall(r'(?:success|Success|SUCCESS|passed|completed|ok)', original_content, re.IGNORECASE))
            
            severity = "low"
            if re.search(r'\b(?:critical|fatal|severe|emergency)\b', original_content, re.IGNORECASE):
                severity = "critical"
            elif re.search(r'\b(?:high|major|important|urgent|error|failed)\b', original_content, re.IGNORECASE):
                severity = "high"
            elif re.search(r'\b(?:medium|moderate|warning)\b', original_content, re.IGNORECASE):
                severity = "medium"
            
            business_impact = 0.3
            if severity == "critical":
                business_impact = 0.9
            elif severity == "high":
                business_impact = 0.7
            elif severity == "medium":
                business_impact = 0.5
            elif metadata.get('status') == 'success':
                business_impact = 0.1
            
            def extract_key_insight(text, max_length=200):
                sentences = re.split(r'[.!?]+', text)
                relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
                return '. '.join(relevant_sentences[:2])[:max_length] if relevant_sentences else "CoT analysis applied"
            
            analysis_result = {
                "failure_summary": f"CoT Pattern Analysis: {extract_key_insight(llm_response, 250)}",
                "root_cause": f"CoT Investigation: Pattern-based analysis of {metadata.get('tool', 'unknown')} {metadata.get('log_type', 'unknown')} content (Confidence: 70%)",
                "fix_suggestion": f"CoT Solution: Apply systematic troubleshooting for {metadata.get('tool', 'unknown')} in {metadata.get('environment', 'unknown')} environment",
                "rollback_plan": f"CoT Rollback: Standard {metadata.get('tool', 'unknown')} rollback procedures with verification",
                "auto_fix": "Manual intervention required - CoT analysis recommends careful review",
                "severity_level": severity,
                "confidence_score": 0.7,
                "confidence_reasoning": "CoT pattern-based analysis applied with moderate confidence",
                "error_count": error_count,
                "warning_count": warning_count,
                "success_indicators": success_indicators,
                "resolution_time_estimate": "2-4 hours" if severity in ["high", "critical"] else "1-2 days",
                "business_impact_score": business_impact,
                "business_impact_reasoning": "CoT pattern-based analysis applied with business impact assessment",
                "technical_complexity": "medium",
                "failure_category": f"{metadata.get('log_type', 'general')}_pattern_cot",
                "affected_components": [metadata.get('tool', 'unknown')],
                "build_duration_seconds": 0,
                "test_pass_rate": 0.0,
                "deployment_success": metadata.get('status') == 'success',
                "monitoring_recommendations": f"CoT Prevention: Systematic monitoring for {metadata.get('tool', 'unknown')} operations",
                "full_synthesis": llm_response,
                "cot_reasoning_applied": True,
                "input_format": "universal",
                "processing_method": "pattern_based_cot"
            }
            
            pattern_span.update_trace(output={"analysis_result": analysis_result})
            return analysis_result
    
    def create_cot_emergency_analysis(self, metadata, error_msg):
        """Emergency CoT analysis when all methods fail"""
        return {
            "failure_summary": f"Emergency CoT Analysis: System error in processing {metadata.get('tool', 'unknown')} {metadata.get('log_type', 'unknown')} content",
            "root_cause": f"CoT Emergency Protocol: Analysis system encountered error - {error_msg[:100]} (Confidence: 30%)",
            "fix_suggestion": f"CoT Emergency Response: Manual review required for {metadata.get('tool', 'unknown')} content",
            "rollback_plan": f"Emergency rollback: Standard {metadata.get('tool', 'unknown')} procedures",
            "auto_fix": "Manual intervention required - CoT emergency protocol",
            "severity_level": "medium",
            "confidence_score": 0.3,
            "confidence_reasoning": "CoT emergency analysis applied with low confidence due to system error",
            "error_count": 0,
            "warning_count": 1,
            "success_indicators": 0,
            "resolution_time_estimate": "immediate",
            "business_impact_score": 0.4,
            "business_impact_reasoning": "CoT emergency analysis applied with business impact assessment",
            "technical_complexity": "low",
            "failure_category": "cot_emergency_analysis",
            "affected_components": ["cot_analysis_service"],
            "build_duration_seconds": 0,
            "test_pass_rate": 0.0,
            "deployment_success": False,
            "monitoring_recommendations": "Monitor CoT analysis service health",
            "full_synthesis": f"Emergency CoT processing due to: {error_msg}",
            "cot_reasoning_applied": True,
            "input_format": "emergency",
            "processing_method": "emergency_cot",
            "system_error": error_msg
        }
    
    def store_in_both_tables(self, analysis_result, metadata):
        """Store CoT analysis in both cicd_analysis and cicd_vectors tables"""
        with langfuse.start_as_current_span(name="store-analysis-data") as store_span:
            store_span.update_trace(
                input={"metadata": metadata, "analysis_keys": list(analysis_result.keys())}
            )
            
            print("💾 Storing universal CoT analysis in both tables...")
            analysis_success = self.store_analysis_table(analysis_result, metadata)
            vector_success = self.store_vector_table(analysis_result, metadata)
            
            storage_result = {
                "analysis_table_success": analysis_success,
                "vector_table_success": vector_success,
                "overall_success": analysis_success and vector_success
            }
            
            store_span.update_trace(output=storage_result)
            
            if analysis_success and vector_success:
                print("✅ Universal CoT analysis stored in both tables")
            else:
                print("⚠️ Partial storage success")
            
            return analysis_success and vector_success
    
    def store_analysis_table(self, analysis_result, metadata):
        """Store in cicd_analysis table"""
        try:
            analysis_data = {
                "log_id": metadata.get('log_id'),
                "correlation_id": metadata.get('correlation_id'),
                "tool": metadata.get('tool'),
                "project": metadata.get('project'),
                "environment": metadata.get('environment'),
                "server": metadata.get('server'),
                "log_type": metadata.get('log_type'),
                "status": metadata.get('status'),
                "llm_model": "llama3.1:8b",
                "analysis": analysis_result
            }
            response = requests.post(f"{self.db_service_url}/store-analysis", json=analysis_data, timeout=60)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error storing in cicd_analysis: {e}")
            return False
    
    def store_vector_table(self, analysis_result, metadata):
        """Store in cicd_vectors table for RAG"""
        try:
            content_parts = [
                analysis_result.get('failure_summary', ''),
                analysis_result.get('root_cause', ''),
                analysis_result.get('fix_suggestion', ''),
                analysis_result.get('monitoring_recommendations', '')
            ]
            content = ' '.join(filter(None, content_parts))
            
            if content:
                embedding = self.embedding_model.encode(content).tolist()
                vector_data = {
                    "content": content,
                    "content_vector": embedding,
                    "correlation_id": metadata.get('correlation_id'),
                    "tool": metadata.get('tool'),
                    "project": metadata.get('project'),
                    "environment": metadata.get('environment'),
                    "log_type": metadata.get('log_type'),
                    "status": metadata.get('status', 'unknown'),
                    "error_pattern": f"{metadata.get('tool')}_{metadata.get('log_type')}_{analysis_result.get('failure_category')}",
                    "solution_type": analysis_result.get('severity_level'),
                    "tags": [
                        metadata.get('tool'), 
                        metadata.get('environment'), 
                        metadata.get('log_type'),
                        metadata.get('status'),
                        analysis_result.get('severity_level'),
                        'universal_cot_analysis'
                    ]
                }
                response = requests.post(f"{self.db_service_url}/store-vector", json=vector_data, timeout=30)
                return response.status_code == 200
            return False
        except Exception as e:
            print(f"❌ Error storing in cicd_vectors: {e}")
            return False
    
    def find_similar_errors(self, error_text, metadata, top_k=3):
        """Query cicd_logs for similar errors using vector search and return insights."""
        try:
            query_vector = self.embedding_model.encode(error_text).tolist()
            search_body = {
                "size": top_k,
                "query": {
                    "script_score": {
                        "query": {"bool": {"must": [
                            {"term": {"tool": metadata.get('tool', '')}},
                            {"term": {"log_type": metadata.get('log_type', '')}}
                        ]}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'content_vector') + 1.0",
                            "params": {"query_vector": query_vector}
                        }
                    }
                },
                "_source": ["log_content", "created_at", "status", "tool", "log_type", "environment", "server"]
            }
            es_host = self.db_service_url.replace('http://', '').replace('https://', '')
            es_url = f"http://{es_host}/cicd_logs/_search"
            resp = requests.post(es_url, json=search_body, timeout=15)
            if resp.status_code == 200:
                hits = resp.json().get('hits', {}).get('hits', [])
                return [h['_source'] for h in hits]
            return []
        except Exception as e:
            print(f"Error in find_similar_errors: {e}")
            return []

# Initialize service
llm_service = UniversalCoTAnalysisService()

@app.route('/analyze', methods=['POST'])
def analyze_universal_content():
    """Universal CoT analysis endpoint for ANY input type"""
    # Create a top-level trace for the entire request
    with langfuse.start_as_current_span(name="analyze-request") as request_span:
        try:
            # Handle ANY input format
            content = ""
            metadata = {}
            
            if request.is_json:
                try:
                    data = request.get_json()
                    content = data.get('content', '')
                    metadata = data.get('metadata', {})
                except:
                    content = request.get_data(as_text=True)
            else:
                content = request.get_data(as_text=True)
            
            request_span.update_trace(
                input={
                    "content_length": len(content),
                    "metadata": metadata,
                    "request_method": request.method,
                    "content_type": request.content_type
                },
                user_id="api_user"
            )
            
            # Validate content
            if not content or len(content.strip()) < 3:
                result = {'status': 'skipped', 'reason': 'Insufficient content for CoT analysis'}
                request_span.update_trace(output=result)
                return jsonify(result), 200
            
            print(f"🔍 Received universal content for CoT analysis ({len(content)} chars)")
            
            # Analyze with universal CoT reasoning
            analysis_result = llm_service.analyze_with_universal_cot(content, metadata)
            
            # Store in both tables
            storage_success = llm_service.store_in_both_tables(analysis_result, metadata)
            
            # Return results
            response_data = {
                'status': 'success',
                'results': {
                    'final_analysis': analysis_result,
                    'chunk_results': [analysis_result],
                    'processing_stats': {
                        'chunks_processed': 1,
                        'processing_time': datetime.utcnow().isoformat(),
                        'model_used': 'llama3.1:8b',
                        'analysis_method': 'Universal Chain-of-Thought reasoning',
                        'input_format': 'any_type',
                        'cot_reasoning_applied': True,
                        'storage_success': storage_success,
                        'tables_updated': ['cicd_analysis', 'cicd_vectors']
                    }
                }
            }
            
            request_span.update_trace(output=response_data)
            return jsonify(response_data), 200
            
        except Exception as e:
            error_response = {'status': 'error', 'error': str(e), 'cot_emergency_applied': True}
            request_span.update_trace(output=error_response)
            print(f"❌ Universal CoT analysis error: {e}")
            return jsonify(error_response), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    with langfuse.start_as_current_span(name="health-check") as health_span:
        try:
            test_response = llm_service.llm.invoke("Hello")
            llm_healthy = len(test_response) > 0
            
            health_data = {
                'status': 'healthy',
                'service': 'Universal CoT LLM Analysis Service',
                'model': 'llama3.1:8b',
                'analysis_method': 'Universal Chain-of-Thought reasoning',
                'input_support': 'ALL formats (JSON, XML, YAML, text, logs, etc.)',
                'cot_steps': 7,
                'storage_targets': ['cicd_analysis', 'cicd_vectors'],
                'llm_healthy': llm_healthy
            }
            
            health_span.update_trace(
                input={"health_check_request": True},
                output=health_data,
                user_id="system"
            )
            
            return jsonify(health_data), 200
        except Exception as e:
            error_data = {'status': 'unhealthy', 'error': str(e)}
            health_span.update_trace(output=error_data)
            return jsonify(error_data), 500

def extract_log_metrics(log_content: str, log_type: str) -> dict:
    """Extract structured metrics from log content based on log type."""
    metrics = {}
    if log_type == 'build':
        match = re.search(r'Build time: ([\dhms :]+)', log_content)
        if not match:
            match = re.search(r'Total time: ([\dhms :]+)', log_content)
        metrics['build_duration'] = match.group(1) if match else None
        metrics['build_success'] = 'BUILD SUCCESS' in log_content or 'Compilation successful' in log_content
        error_count = len(re.findall(r'ERROR:', log_content))
        metrics['build_error_count'] = error_count
        warning_count = len(re.findall(r'WARNING:', log_content))
        metrics['build_warning_count'] = warning_count
        test_match = re.search(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)', log_content)
        if test_match:
            metrics['tests_run'] = int(test_match.group(1))
            metrics['test_failures'] = int(test_match.group(2))
            metrics['test_errors'] = int(test_match.group(3))
            metrics['test_skipped'] = int(test_match.group(4))
    elif log_type == 'deployment':
        match = re.search(r'Deployment duration: ([\dhms :]+)', log_content)
        if not match:
            match = re.search(r'Deployment completed successfully.*?Deployment duration: ([\dhms :]+)', log_content)
        metrics['deployment_duration'] = match.group(1) if match else None
        metrics['deployment_success'] = 'Deployment completed successfully' in log_content
        error_count = len(re.findall(r'ERROR:', log_content))
        metrics['deployment_error_count'] = error_count
        metrics['deployment_fatal'] = 'FATAL:' in log_content
        metrics['rollback_initiated'] = 'Rollback initiated' in log_content
    elif log_type == 'git':
        error_lines = re.findall(r'ERROR: (.+)', log_content)
        metrics['git_errors'] = error_lines
        metrics['git_fatal'] = 'FATAL:' in log_content
    elif log_type == 'sonarqube':
        match = re.search(r'Code coverage: ([\d.]+)%', log_content)
        metrics['code_coverage'] = float(match.group(1)) if match else None
        match = re.search(r'Duplicated lines: ([\d.]+)%', log_content)
        metrics['duplicated_lines'] = float(match.group(1)) if match else None
        match = re.search(r'Technical debt: ([\d.]+) hours', log_content)
        metrics['technical_debt_hours'] = float(match.group(1)) if match else None
        match = re.search(r'Bugs: (\d+)', log_content)
        metrics['bugs'] = int(match.group(1)) if match else None
        match = re.search(r'Vulnerabilities: (\d+)', log_content)
        metrics['vulnerabilities'] = int(match.group(1)) if match else None
        match = re.search(r'Code smells: (\d+)', log_content)
        metrics['code_smells'] = int(match.group(1)) if match else None
        metrics['quality_gate_passed'] = 'Quality gate failed' not in log_content
        match = re.search(r'Analysis duration: ([\dhms :]+)', log_content)
        metrics['analysis_duration'] = match.group(1) if match else None
    elif log_type == 'test':
        match = re.search(r'Found (\d+) test cases', log_content)
        metrics['test_cases_found'] = int(match.group(1)) if match else None
        failed_tests = re.findall(r'FAILED ([^\s]+) - ([^\n]+)', log_content)
        metrics['failed_tests'] = [{'test': t, 'reason': r} for t, r in failed_tests]
        error_count = len(re.findall(r'ERROR:', log_content))
        metrics['test_error_count'] = error_count
        match = re.search(r'Coverage: ([\d.]+)%', log_content)
        metrics['test_coverage'] = float(match.group(1)) if match else None
        metrics['test_fatal'] = 'FATAL:' in log_content
    return metrics

# Patch into UniversalCoTAnalysisService: add metrics extraction to analysis output
old_analyze_with_universal_cot = UniversalCoTAnalysisService.analyze_with_universal_cot
def analyze_with_universal_cot_with_metrics(self, content, metadata):
    log_type = metadata.get('log_type', '').lower()
    metrics = extract_log_metrics(content, log_type)
    analysis = old_analyze_with_universal_cot(self, content, metadata)
    return {
        'llm_analysis': analysis,
        'metrics': metrics,
        'log_type': log_type,
        'raw_log': content,
        'metadata': metadata
    }
UniversalCoTAnalysisService.analyze_with_universal_cot = analyze_with_universal_cot_with_metrics

if __name__ == '__main__':
    print("🧠 Starting Universal Chain-of-Thought LLM Analysis Service")
    print("🦙 Model: Llama 3.1 8B with universal CoT reasoning")
    print("📥 Input: ANY format (JSON, XML, YAML, text, logs, binary, etc.)")
    print("🔧 CoT Steps: Format ID → Parsing → Issue Detection → Context → Root Cause → Solution → Prevention")
    print("📊 Storage: Both cicd_analysis and cicd_vectors tables")
    print("⚡ Features: Universal input handling, systematic reasoning, dual storage")
    print("📊 Langfuse Tracing: Enabled for complete observability")
    
    # Flush any remaining Langfuse events on startup
    langfuse.flush()
    
    app.run(debug=False, port=5003, use_reloader=False)
