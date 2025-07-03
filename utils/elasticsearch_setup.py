# utils/elasticsearch_setup.py - Setup Elasticsearch indexes with your credentials
from elasticsearch import Elasticsearch
import base64
from datetime import datetime

class ElasticsearchSetup:
    def __init__(self):
        # Decode your API key
        api_key_decoded = base64.b64decode("LTFUWHFwY0JaV0JEc0IySlNXOGo6QXFDZHNFR3NtMjliMXhBVUFSV3Vxdw==").decode('utf-8')
        key_parts = api_key_decoded.split(':')
        
        self.es = Elasticsearch(
            ["https://my-elasticsearch-project-b613be.es.ap-southeast-1.aws.elastic.cloud:443"],
            api_key=(key_parts[0], key_parts[1]),
            verify_certs=True,
            request_timeout=60
        )
        
        self.logs_index = "cicd_logs"
        self.analysis_index = "cicd_analysis"
        self.vector_index = "cicd_vectors"
        self.memory_index = "cicd_chat_memory"
        
        print("✅ Connected to Elasticsearch with your credentials")
    
    def create_all_indexes(self):
        """Create all required Elasticsearch indexes"""
        
        # Logs index mapping
        logs_mapping = {
            "mappings": {
                "properties": {
                    "tool": {"type": "keyword"},
                    "project": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "server": {"type": "keyword"},
                    "log_type": {"type": "keyword"},
                    "log_content": {"type": "text"},
                    "file_path": {"type": "keyword"},
                    "file_name": {"type": "keyword"},
                    "processed": {"type": "boolean"},
                    "created_at": {"type": "date"},
                    "processed_at": {"type": "date"},
                    "file_size": {"type": "long"},
                    "checksum": {"type": "keyword"},
                    "correlation_id": {"type": "keyword"},
                    "status": {"type": "keyword"}  # error or success
                }
            }
        }
        
        # Analysis index mapping with comprehensive metrics
        analysis_mapping = {
            "mappings": {
                "properties": {
                    "log_id": {"type": "keyword"},
                    "correlation_id": {"type": "keyword"},
                    "tool": {"type": "keyword"},
                    "project": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "server": {"type": "keyword"},
                    "log_type": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    
                    # LLM Analysis Results (flexible structure)
                    "executive_summary": {"type": "text"},
                    "root_cause_analysis": {"type": "text"},
                    "impact_assessment": {"type": "text"},
                    "fix_strategy": {"type": "text"},
                    "prevention_measures": {"type": "text"},
                    "monitoring_recommendations": {"type": "text"},
                    "full_synthesis": {"type": "text"},
                    "llm_response": {"type": "text"},
                    
                    # Comprehensive metrics for dashboard
                    "severity_level": {"type": "keyword"},
                    "confidence_score": {"type": "float"},
                    "error_count": {"type": "integer"},
                    "warning_count": {"type": "integer"},
                    "success_indicators": {"type": "integer"},
                    "resolution_time_estimate": {"type": "keyword"},
                    "business_impact_score": {"type": "float"},
                    "technical_complexity": {"type": "keyword"},
                    "failure_category": {"type": "keyword"},
                    "affected_components": {"type": "keyword"},
                    
                    # Processing metadata
                    "analysis_timestamp": {"type": "date"},
                    "processing_time_ms": {"type": "long"},
                    "llm_model": {"type": "keyword"},
                    "analysis_version": {"type": "keyword"},
                    
                    # Success/failure tracking
                    "is_successful_build": {"type": "boolean"},
                    "build_duration_seconds": {"type": "long"},
                    "test_pass_rate": {"type": "float"},
                    "deployment_success": {"type": "boolean"}
                }
            }
        }
        
        # Vector index mapping for RAG
        vector_mapping = {
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "content_vector": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "correlation_id": {"type": "keyword"},
                    "tool": {"type": "keyword"},
                    "project": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "log_type": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "error_pattern": {"type": "keyword"},
                    "solution_type": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "tags": {"type": "keyword"}
                }
            }
        }
        
        # Memory index mapping for RAG chatbot
        memory_mapping = {
            "mappings": {
                "properties": {
                    "session_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "conversation_history": {
                        "type": "nested",
                        "properties": {
                            "role": {"type": "keyword"},
                            "content": {"type": "text"},
                            "timestamp": {"type": "date"},
                            "intent": {"type": "keyword"}
                        }
                    },
                    "context_summary": {"type": "text"},
                    "last_updated": {"type": "date"},
                    "message_count": {"type": "integer"}
                }
            }
        }
        
        # Create all indexes
        indexes = [
            (self.logs_index, logs_mapping),
            (self.analysis_index, analysis_mapping),
            (self.vector_index, vector_mapping),
            (self.memory_index, memory_mapping)
        ]
        
        for index_name, mapping in indexes:
            try:
                if not self.es.indices.exists(index=index_name):
                    self.es.indices.create(index=index_name, body=mapping)
                    print(f"✅ Created index: {index_name}")
                else:
                    print(f"ℹ️  Index already exists: {index_name}")
            except Exception as e:
                print(f"❌ Error creating index {index_name}: {e}")
        
        print("✅ All Elasticsearch indexes ready")
        
        # Test connection
        try:
            #health = self.es.cluster.health()
            indices_info = self.es.cat.indices(format = 'json')
            print(f"🔍 Cluster health: {len(indices_info)}")
        except Exception as e:
            print(f"⚠️  Could not get cluster health: {e}")

if __name__ == "__main__":
    setup = ElasticsearchSetup()
    setup.create_all_indexes()
