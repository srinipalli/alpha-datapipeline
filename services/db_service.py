# services/db_service.py - Database operations service with all helper functions
import os
import logging
from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from datetime import datetime, timedelta
import uuid
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class DatabaseService:
    def __init__(self):
        """Initialize Elasticsearch connection with hardcoded credentials"""
        try:
            # Hardcoded Elasticsearch configuration
            es_host = "https://a774a75424564c46a6264388ef74dcd6.us-central1.gcp.cloud.es.io:443"
            es_api_key = "WVBtMXdaY0JZeEpjNHpvYm1ybXI6Ti1RY1U0RTZOWXRuRGZiS183MVRxdw=="
            
            if not all([es_host, es_api_key]):
                raise ValueError("Elasticsearch host or API key not configured")
            
            # Initialize Elasticsearch client
            self.es = Elasticsearch(
                [es_host],
                api_key=es_api_key,
                verify_certs=True,
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            if not self.es.ping():
                raise ConnectionError("Cannot connect to Elasticsearch")
            
            # Index names
            self.logs_index = "cicd_logs"
            self.analysis_index = "cicd_analysis"
            self.vector_index = "cicd_vectors"
            
            # Create indices if they don't exist
            self._ensure_indices()
            
            logger.info("✅ Database service connected to Elasticsearch")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DatabaseService: {e}")
            raise
    
    def _ensure_indices(self):
        """Create indices with proper mappings if they don't exist"""
        indices_config = {
            self.logs_index: {
                "mappings": {
                    "properties": {
                        "tool": {"type": "keyword"},
                        "project": {"type": "keyword"},
                        "environment": {"type": "keyword"},
                        "server": {"type": "keyword"},
                        "log_type": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "processed": {"type": "boolean"},
                        "created_at": {"type": "date"},
                        "processed_at": {"type": "date"},
                        "file_size": {"type": "long"},
                        "checksum": {"type": "keyword"},
                        "correlation_id": {"type": "keyword"},
                        "log_content": {"type": "text"},
                        "file_path": {"type": "keyword"},
                        "file_name": {"type": "keyword"}
                    }
                }
            },
            self.analysis_index: {
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
                        "severity_level": {"type": "keyword"},
                        "confidence_score": {"type": "float"},
                        "analysis_timestamp": {"type": "date"},
                        "executive_summary": {"type": "text"},
                        "root_cause_analysis": {"type": "text"},
                        "impact_assessment": {"type": "text"},
                        "fix_strategy": {"type": "text"},
                        "affected_components": {"type": "keyword"},
                        "deployment_success": {"type": "boolean"},
                        "build_duration_seconds": {"type": "long"},
                        "error_count": {"type": "integer"},
                        "warning_count": {"type": "integer"},
                        "success_indicators": {"type": "integer"},
                        "business_impact_score": {"type": "float"}
                    }
                }
            }
        }
        
        for index_name, config in indices_config.items():
            try:
                if not self.es.indices.exists(index=index_name):
                    self.es.indices.create(index=index_name, body=config)
                    logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.error(f"Error creating index {index_name}: {e}")
                raise
        
        # Create vector index separately
        try:
            if not self.es.indices.exists(index=self.vector_index):
                vector_config = {
                    "mappings": {
                        "properties": {
                            "content": {"type": "text"},
                            "tool": {"type": "keyword"},
                            "project": {"type": "keyword"},
                            "environment": {"type": "keyword"},
                            "log_type": {"type": "keyword"},
                            "status": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "tags": {"type": "keyword"}
                        }
                    }
                }
                self.es.indices.create(index=self.vector_index, body=vector_config)
                logger.info(f"Created vector index: {self.vector_index}")
        except Exception as e:
            logger.warning(f"Could not create vector index: {e}")

# Initialize service
try:
    db_service = DatabaseService()
except Exception as e:
    logger.error(f"Failed to initialize database service: {e}")
    db_service = None

# Helper Functions for Frontend Integration
def format_time_ago(timestamp_str):
    """Format timestamp as 'X time ago'"""
    try:
        if not timestamp_str:
            return 'Never'
        
        # Parse ISO timestamp
        if isinstance(timestamp_str, str):
            # Handle different timestamp formats
            if 'T' in timestamp_str:
                if timestamp_str.endswith('Z'):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = timestamp_str
        
        now = datetime.utcnow()
        if timestamp.tzinfo is not None:
            # Convert to UTC for comparison
            timestamp = timestamp.replace(tzinfo=None)
        
        diff = now - timestamp
        total_seconds = int(diff.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"
        else:
            days = total_seconds // 86400
            return f"{days}d ago"
            
    except Exception as e:
        logger.error(f"Error formatting timestamp {timestamp_str}: {e}")
        return 'Unknown'

def get_env_status(env_buckets):
    """Get environment status from aggregation buckets"""
    try:
        env_status = {}
        
        for bucket in env_buckets:
            env_name = bucket['key']
            doc_count = bucket['doc_count']
            
            # Determine status based on document count and other factors
            if doc_count == 0:
                status = 'unknown'
            elif doc_count < 5:
                status = 'warning'
            else:
                # Check for success indicators if available
                if 'success_rate' in bucket and bucket['success_rate']['value'] is not None:
                    success_rate = bucket['success_rate']['value']
                    if success_rate > 0.8:
                        status = 'success'
                    elif success_rate > 0.5:
                        status = 'warning'
                    else:
                        status = 'error'
                else:
                    status = 'success'  # Default to success if no specific data
            
            env_status[env_name] = status
        
        return env_status
        
    except Exception as e:
        logger.error(f"Error getting environment status: {e}")
        return {}

def build_metrics_query(tool, project, filters):
    """Build Elasticsearch query for metrics"""
    try:
        # Base query filters
        must_clauses = [
            {"term": {"tool": tool}},
            {"term": {"project": project}}
        ]
        
        # Add optional filters
        if filters.get('stage') and filters['stage'] != 'all':
            must_clauses.append({"term": {"log_type": filters['stage']}})
        
        if filters.get('server') and filters['server'] != 'all':
            must_clauses.append({"term": {"server": filters['server']}})
        
        if filters.get('environment') and filters['environment'] != 'all':
            must_clauses.append({"term": {"environment": filters['environment']}})
        
        # Time filter
        if filters.get('timeFilter') and filters['timeFilter'] != 'all':
            time_range = get_time_range(filters['timeFilter'])
            must_clauses.append({
                "range": {
                    "analysis_timestamp": {
                        "gte": time_range['start'],
                        "lte": time_range['end']
                    }
                }
            })
        
        # Build complete query with aggregations
        query = {
            "query": {
                "bool": {"must": must_clauses}
            },
            "size": 0,
            "aggs": {
                "success_rate": {
                    "avg": {"field": "deployment_success"}
                },
                "error_rate": {
                    "avg": {"field": "error_count"}
                },
                "avg_build_time": {
                    "avg": {"field": "build_duration_seconds"}
                },
                "total_builds": {
                    "value_count": {"field": "log_id"}
                },
                "failed_builds": {
                    "filter": {"term": {"status": "error"}},
                    "aggs": {
                        "count": {"value_count": {"field": "log_id"}}
                    }
                },
                "success_rate_history": {
                    "date_histogram": {
                        "field": "analysis_timestamp",
                        "calendar_interval": "1d",
                        "min_doc_count": 0
                    },
                    "aggs": {
                        "success_rate": {
                            "avg": {"field": "deployment_success"}
                        }
                    }
                },
                "stages": {
                    "terms": {"field": "log_type", "size": 20}
                },
                "servers": {
                    "terms": {"field": "server", "size": 50}
                },
                "environments": {
                    "terms": {"field": "environment", "size": 10}
                }
            }
        }
        
        return query
        
    except Exception as e:
        logger.error(f"Error building metrics query: {e}")
        return {"query": {"match_all": {}}, "size": 0}

def build_analyses_query(tool, project, filters):
    """Build Elasticsearch query for analyses"""
    try:
        # Base query filters
        must_clauses = [
            {"term": {"tool": tool}},
            {"term": {"project": project}}
        ]
        
        # Add optional filters
        if filters.get('stage') and filters['stage'] != 'all':
            must_clauses.append({"term": {"log_type": filters['stage']}})
        
        if filters.get('server') and filters['server'] != 'all':
            must_clauses.append({"term": {"server": filters['server']}})
        
        if filters.get('logType') and filters['logType'] != 'all':
            must_clauses.append({"term": {"log_type": filters['logType']}})
        
        if filters.get('environment') and filters['environment'] != 'all':
            must_clauses.append({"term": {"environment": filters['environment']}})
        
        # Time filter
        if filters.get('timeFilter') and filters['timeFilter'] != 'all':
            time_range = get_time_range(filters['timeFilter'])
            must_clauses.append({
                "range": {
                    "analysis_timestamp": {
                        "gte": time_range['start'],
                        "lte": time_range['end']
                    }
                }
            })
        
        query = {
            "query": {
                "bool": {"must": must_clauses}
            },
            "sort": [
                {"analysis_timestamp": {"order": "desc"}}
            ],
            "size": 100  # Limit results
        }
        
        return query
        
    except Exception as e:
        logger.error(f"Error building analyses query: {e}")
        return {"query": {"match_all": {}}, "sort": [{"analysis_timestamp": {"order": "desc"}}], "size": 10}

def transform_metrics_response(response):
    """Transform Elasticsearch metrics response for frontend"""
    try:
        aggs = response.get('aggregations', {})
        
        # Extract basic metrics
        success_rate = aggs.get('success_rate', {}).get('value', 0) or 0
        error_rate = aggs.get('error_rate', {}).get('value', 0) or 0
        avg_build_time = aggs.get('avg_build_time', {}).get('value', 0) or 0
        total_builds = aggs.get('total_builds', {}).get('value', 0) or 0
        failed_builds = aggs.get('failed_builds', {}).get('count', {}).get('value', 0) or 0
        
        # Transform success rate history
        success_history = []
        if 'success_rate_history' in aggs:
            for bucket in aggs['success_rate_history']['buckets']:
                success_history.append({
                    'date': bucket['key_as_string'],
                    'value': int((bucket['success_rate']['value'] or 0) * 100)
                })
        
        # Transform stages
        stages = []
        if 'stages' in aggs:
            for bucket in aggs['stages']['buckets']:
                stages.append({
                    'name': bucket['key'],
                    'label': bucket['key'].replace('_', ' ').title(),
                    'count': bucket['doc_count']
                })
        
        # Transform servers
        servers = []
        if 'servers' in aggs:
            for bucket in aggs['servers']['buckets']:
                servers.append({
                    'id': bucket['key'],
                    'name': bucket['key'],
                    'count': bucket['doc_count'],
                    'health': min(100, max(60, 100 - (bucket['doc_count'] * 2)))  # Mock health calculation
                })
        
        # Transform environments
        log_types = []
        if 'environments' in aggs:
            for bucket in aggs['environments']['buckets']:
                log_types.append({
                    'type': bucket['key'],
                    'label': bucket['key'].title(),
                    'count': bucket['doc_count']
                })
        
        metrics = {
            'success_rate': int(success_rate * 100),
            'error_rate': int(error_rate),
            'avg_build_time': int(avg_build_time / 60) if avg_build_time > 0 else 0,  # Convert to minutes
            'deployment_count': int(total_builds),
            'total_builds': int(total_builds),
            'failed_builds': int(failed_builds),
            'success_rate_history': success_history,
            'build_time_distribution': success_history,  # Reuse for demo
            'stages': stages,
            'servers': servers,
            'logTypes': log_types,
            'last_deployment': format_time_ago(datetime.utcnow().isoformat()),
            'avg_resolution_time': '2-4 hours'
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error transforming metrics response: {e}")
        return {
            'success_rate': 0,
            'error_rate': 0,
            'avg_build_time': 0,
            'deployment_count': 0,
            'stages': [],
            'servers': [],
            'logTypes': []
        }

def get_time_range(time_filter):
    """Get time range for filtering"""
    try:
        now = datetime.utcnow()
        
        if time_filter == '1d':
            start = now - timedelta(days=1)
        elif time_filter == '7d':
            start = now - timedelta(days=7)
        elif time_filter == '30d':
            start = now - timedelta(days=30)
        else:
            start = now - timedelta(days=365)  # Default to 1 year
        
        return {
            'start': start.isoformat(),
            'end': now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting time range: {e}")
        return {
            'start': (datetime.utcnow() - timedelta(days=30)).isoformat(),
            'end': datetime.utcnow().isoformat()
        }

def validate_required_fields(data: Dict, required_fields: List[str]) -> Optional[str]:
    """Validate that all required fields are present in data"""
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"
    return None

@app.before_request
def check_db_service():
    """Ensure database service is available"""
    if db_service is None:
        return jsonify({'error': 'Database service unavailable'}), 503

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/check-file/<checksum>', methods=['GET'])
def check_file_exists(checksum: str):
    """Check if file exists in database"""
    if not checksum or len(checksum) < 10:
        return jsonify({'error': 'Invalid checksum'}), 400
    
    try:
        response = db_service.es.search(
            index=db_service.logs_index,
            body={"query": {"term": {"checksum": checksum}}},
            size=1
        )
        exists = response['hits']['total']['value'] > 0
        return jsonify({'exists': exists}), 200
        
    except es_exceptions.NotFoundError:
        return jsonify({'exists': False}), 200
    except Exception as e:
        logger.error(f"Error checking file: {e}")
        return jsonify({'error': 'Database query failed'}), 500

@app.route('/store-log', methods=['POST'])
def store_log():
    """Store log in database"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['tool', 'project', 'environment', 'server', 'log_type', 
                          'log_content', 'file_path', 'file_size', 'checksum']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Sanitize and prepare document
        doc = {
            "tool": str(data['tool'])[:50],
            "project": str(data['project'])[:50],
            "environment": str(data['environment'])[:20],
            "server": str(data['server'])[:50],
            "log_type": str(data['log_type'])[:30],
            "status": str(data.get('status', 'unknown'))[:20],
            "log_content": str(data['log_content'])[:100000],
            "file_path": str(data['file_path'])[:500],
            "file_name": str(data['file_path']).split('/')[-1][:100],
            "processed": False,
            "created_at": datetime.utcnow().isoformat(),
            "processed_at": None,
            "file_size": int(data['file_size']) if str(data['file_size']).isdigit() else 0,
            "checksum": str(data['checksum'])[:64],
            "correlation_id": str(data.get('correlation_id', str(uuid.uuid4())[:8]))[:20]
        }
        
        result = db_service.es.index(index=db_service.logs_index, body=doc)
        logger.info(f"✅ Stored log: {data['file_path']} (ID: {result['_id']})")
        return jsonify({'status': 'success', 'log_id': result['_id']}), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': 'Invalid data format'}), 400
    except Exception as e:
        logger.error(f"Error storing log: {e}")
        return jsonify({'error': 'Failed to store log'}), 500

@app.route('/get-unprocessed-logs', methods=['GET'])
def get_unprocessed_logs():
    """Get logs that need LLM analysis"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 0))
        size = min(int(request.args.get('size', 20)), 100)
        from_param = page * size
        
        response = db_service.es.search(
            index=db_service.logs_index,
            body={
                "query": {"term": {"processed": False}},
                "sort": [{"created_at": {"order": "asc"}}],
                "size": size,
                "from": from_param
            }
        )
        
        logs = []
        for hit in response['hits']['hits']:
            logs.append({
                "log_id": hit['_id'],
                "data": hit['_source']
            })
        
        return jsonify({
            'logs': logs, 
            'count': len(logs),
            'total': response['hits']['total']['value'],
            'page': page
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid pagination parameters'}), 400
    except Exception as e:
        logger.error(f"Error getting unprocessed logs: {e}")
        return jsonify({'error': 'Failed to retrieve logs'}), 500

@app.route('/store-analysis', methods=['POST'])
def store_analysis():
    """Store LLM analysis results (supports new format with metrics)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['log_id', 'tool', 'project', 'environment', 'server', 'log_type']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        analysis_data = data.get('analysis', {})
        
        # Support new format: if analysis_data contains 'llm_analysis' and 'metrics', merge them
        if 'llm_analysis' in analysis_data and 'metrics' in analysis_data:
            merged = dict(analysis_data['llm_analysis'])
            merged.update(analysis_data['metrics'])
            analysis_data = merged
        
        # Prepare analysis document with input sanitization
        analysis_doc = {
            "log_id": str(data['log_id'])[:50],
            "correlation_id": str(data.get('correlation_id', ''))[:20],
            "tool": str(data['tool'])[:50],
            "project": str(data['project'])[:50],
            "environment": str(data['environment'])[:20],
            "server": str(data['server'])[:50],
            "log_type": str(data['log_type'])[:30],
            "status": str(data.get('status', 'unknown'))[:20],
            
            # LLM Analysis Results (with length limits)
            "executive_summary": str(analysis_data.get('executive_summary', analysis_data.get('failure_summary', '')))[:5000],
            "root_cause_analysis": str(analysis_data.get('root_cause_analysis', analysis_data.get('root_cause', '')))[:10000],
            "impact_assessment": str(analysis_data.get('impact_assessment', ''))[:5000],
            "fix_strategy": str(analysis_data.get('fix_strategy', ''))[:10000],
            "prevention_measures": str(analysis_data.get('prevention_measures', ''))[:5000],
            "monitoring_recommendations": str(analysis_data.get('monitoring_recommendations', ''))[:5000],
            "full_synthesis": str(analysis_data.get('full_synthesis', ''))[:15000],
            "llm_response": str(analysis_data.get('llm_response', ''))[:20000],
            
            # Metrics with validation
            "severity_level": str(analysis_data.get('severity_level', 'medium'))[:20],
            "confidence_score": max(0.0, min(1.0, float(analysis_data.get('confidence_score', 0.8)))),
            "error_count": max(0, int(analysis_data.get('error_count', 0))),
            "warning_count": max(0, int(analysis_data.get('warning_count', 0))),
            "success_indicators": max(0, int(analysis_data.get('success_indicators', 0))),
            "resolution_time_estimate": str(analysis_data.get('resolution_time_estimate', 'unknown'))[:50],
            "business_impact_score": max(0.0, min(1.0, float(analysis_data.get('business_impact_score', 0.5)))),
            "technical_complexity": str(analysis_data.get('technical_complexity', 'medium'))[:20],
            "failure_category": str(analysis_data.get('failure_category', 'general'))[:50],
            "affected_components": analysis_data.get('affected_components', [])[:20],
            
            # Success/failure tracking
            "is_successful_build": data.get('status') == 'success',
            "build_duration_seconds": max(0, int(analysis_data.get('build_duration_seconds', 0))),
            "test_pass_rate": max(0.0, min(1.0, float(analysis_data.get('test_pass_rate', 0.0)))),
            "deployment_success": bool(analysis_data.get('deployment_success', False)),
            
            # Additional metrics from new format (if present)
            "build_duration": analysis_data.get('build_duration'),
            "build_success": analysis_data.get('build_success'),
            "build_error_count": analysis_data.get('build_error_count'),
            "build_warning_count": analysis_data.get('build_warning_count'),
            "tests_run": analysis_data.get('tests_run'),
            "test_failures": analysis_data.get('test_failures'),
            "test_errors": analysis_data.get('test_errors'),
            "test_skipped": analysis_data.get('test_skipped'),
            "deployment_duration": analysis_data.get('deployment_duration'),
            "deployment_error_count": analysis_data.get('deployment_error_count'),
            "deployment_fatal": analysis_data.get('deployment_fatal'),
            "rollback_initiated": analysis_data.get('rollback_initiated'),
            "git_errors": analysis_data.get('git_errors'),
            "git_fatal": analysis_data.get('git_fatal'),
            "code_coverage": analysis_data.get('code_coverage'),
            "duplicated_lines": analysis_data.get('duplicated_lines'),
            "technical_debt_hours": analysis_data.get('technical_debt_hours'),
            "bugs": analysis_data.get('bugs'),
            "vulnerabilities": analysis_data.get('vulnerabilities'),
            "code_smells": analysis_data.get('code_smells'),
            "quality_gate_passed": analysis_data.get('quality_gate_passed'),
            "analysis_duration": analysis_data.get('analysis_duration'),
            "test_cases_found": analysis_data.get('test_cases_found'),
            "failed_tests": analysis_data.get('failed_tests'),
            "test_error_count": analysis_data.get('test_error_count'),
            "test_coverage": analysis_data.get('test_coverage'),
            "test_fatal": analysis_data.get('test_fatal'),
            
            # Processing metadata
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": max(0, int(analysis_data.get('processing_time_ms', 0))),
            "llm_model": str(data.get('llm_model', 'llama3.1:8b'))[:50],
            "analysis_version": "1.0"
        }
        
        result = db_service.es.index(index=db_service.analysis_index, body=analysis_doc)
        
        # Mark log as processed
        db_service.es.update(
            index=db_service.logs_index,
            id=data['log_id'],
            body={
                "doc": {
                    "processed": True,
                    "processed_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.info(f"✅ Stored analysis for log {data['log_id']}")
        return jsonify({'status': 'success', 'analysis_id': result['_id']}), 200
        
    except (ValueError, TypeError) as e:
        logger.error(f"Validation error in store_analysis: {e}")
        return jsonify({'error': 'Invalid data format'}), 400
    except Exception as e:
        logger.error(f"Error storing analysis: {e}")
        return jsonify({'error': 'Failed to store analysis'}), 500

@app.route('/store-vector', methods=['POST'])
def store_vector():
    """Store vector for RAG"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['content', 'tool', 'project', 'environment', 'log_type']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        vector_doc = {
            "content": str(data['content'])[:10000],
            "correlation_id": str(data.get('correlation_id', ''))[:20],
            "tool": str(data['tool'])[:50],
            "project": str(data['project'])[:50],
            "environment": str(data['environment'])[:20],
            "log_type": str(data['log_type'])[:30],
            "status": str(data.get('status', 'unknown'))[:20],
            "error_pattern": str(data.get('error_pattern', ''))[:500],
            "solution_type": str(data.get('solution_type', ''))[:100],
            "created_at": datetime.utcnow().isoformat(),
            "tags": data.get('tags', [])[:10]
        }
        
        # Only add vector if provided
        if 'content_vector' in data:
            content_vector = data['content_vector']
            if isinstance(content_vector, list):
                vector_doc['content_vector'] = content_vector
        
        result = db_service.es.index(index=db_service.vector_index, body=vector_doc)
        return jsonify({'status': 'success', 'vector_id': result['_id']}), 200
        
    except ValueError as e:
        logger.error(f"Validation error in store_vector: {e}")
        return jsonify({'error': 'Invalid data format'}), 400
    except Exception as e:
        logger.error(f"Error storing vector: {e}")
        return jsonify({'error': 'Failed to store vector'}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    try:
        stats = {}
        
        # Use multi-search for better performance
        msearch_body = []
        
        # Total logs
        msearch_body.extend([
            {"index": db_service.logs_index},
            {"query": {"match_all": {}}, "size": 0}
        ])
        
        # Processed logs
        msearch_body.extend([
            {"index": db_service.logs_index},
            {"query": {"term": {"processed": True}}, "size": 0}
        ])
        
        # Error logs
        msearch_body.extend([
            {"index": db_service.logs_index},
            {"query": {"term": {"status": "error"}}, "size": 0}
        ])
        
        # Success logs
        msearch_body.extend([
            {"index": db_service.logs_index},
            {"query": {"term": {"status": "success"}}, "size": 0}
        ])
        
        # Analyses
        msearch_body.extend([
            {"index": db_service.analysis_index},
            {"query": {"match_all": {}}, "size": 0}
        ])
        
        # Vectors
        msearch_body.extend([
            {"index": db_service.vector_index},
            {"query": {"match_all": {}}, "size": 0}
        ])
        
        response = db_service.es.msearch(body=msearch_body)
        
        stats = {
            'total_logs': response['responses'][0]['hits']['total']['value'],
            'processed_logs': response['responses'][1]['hits']['total']['value'],
            'error_logs': response['responses'][2]['hits']['total']['value'],
            'success_logs': response['responses'][3]['hits']['total']['value'],
            'total_analyses': response['responses'][4]['hits']['total']['value'],
            'total_vectors': response['responses'][5]['hits']['total']['value']
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Failed to retrieve statistics'}), 500

# Frontend Integration Endpoints
@app.route('/projects', methods=['GET'])
def get_projects():
    """Get unique projects from logs"""
    try:
        # Query Elasticsearch for unique projects
        query = {
            "size": 0,
            "aggs": {
                "tools": {
                    "terms": {"field": "tool"},
                    "aggs": {
                        "projects": {
                            "terms": {"field": "project"},
                            "aggs": {
                                "environments": {"terms": {"field": "environment"}},
                                "last_build": {"max": {"field": "created_at"}},
                                "success_rate": {"avg": {"field": "deployment_success"}}
                            }
                        }
                    }
                }
            }
        }
        
        response = db_service.es.search(index=db_service.logs_index, body=query)
        
        projects = []
        for tool_bucket in response['aggregations']['tools']['buckets']:
            tool = tool_bucket['key']
            for project_bucket in tool_bucket['projects']['buckets']:
                project = project_bucket['key']
                projects.append({
                    'name': project,
                    'tool': tool,
                    'successRate': int((project_bucket['success_rate']['value'] or 0) * 100),
                    'lastBuild': format_time_ago(project_bucket['last_build']['value_as_string']),
                    'environments': project_bucket['environments']['doc_count'],
                    'envStatus': get_env_status(project_bucket['environments']['buckets'])
                })
        
        return jsonify(projects), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/elasticsearch-query', methods=['POST'])
def elasticsearch_query():
    """Direct Elasticsearch query endpoint"""
    try:
        data = request.get_json()
        index = data.get('index', db_service.logs_index)
        query = data.get('query', {})
        
        response = db_service.es.search(index=index, body=query)
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/project-metrics/<tool>/<project>', methods=['GET'])
def get_project_metrics(tool, project):
    """Get metrics for specific project"""
    try:
        filters = request.args.to_dict()
        
        # Build Elasticsearch query based on filters
        query = build_metrics_query(tool, project, filters)
        
        response = db_service.es.search(index=db_service.analysis_index, body=query)
        metrics = transform_metrics_response(response)
        
        return jsonify(metrics), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/project-analyses/<tool>/<project>', methods=['GET'])
def get_project_analyses(tool, project):
    """Get analyses for specific project"""
    try:
        filters = request.args.to_dict()
        
        query = build_analyses_query(tool, project, filters)
        
        response = db_service.es.search(index=db_service.analysis_index, body=query)
        analyses = [hit['_source'] for hit in response['hits']['hits']]
        
        return jsonify(analyses), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        if db_service is None:
            return jsonify({'status': 'unhealthy', 'error': 'Database service not initialized'}), 500
        
        # Test Elasticsearch connection
        health_info = db_service.es.cluster.health()
        
        return jsonify({
            'status': 'healthy', 
            'service': 'database',
            'elasticsearch_status': health_info['status'],
            'cluster_name': health_info['cluster_name'],
            'active_shards': health_info['active_shards']
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': 'Elasticsearch connection failed'}), 500

if __name__ == '__main__':
    if db_service is None:
        logger.error("Cannot start service - database initialization failed")
        exit(1)
    
    logger.info("💾 Starting Database Service")
    app.run(debug=False, port=5001, host='0.0.0.0', use_reloader=False)
