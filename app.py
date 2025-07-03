# app.py - Complete parallel processing system
import subprocess
import time
import threading
import requests
import os
from datetime import datetime
from utils.folder_creator import DemoFolderCreator
from utils.elasticsearch_setup import ElasticsearchSetup
import concurrent.futures
import queue
import json

class ParallelCICDAnalyzer:
    def __init__(self):
        self.service_urls = {
            'db_service': 'http://localhost:5001',
            'folder_scanner': 'http://localhost:5002',
            'llm_analysis': 'http://localhost:5003',
            'rag_chatbot': 'http://localhost:5004'
        }
        
        # Parallel processing flags
        self.system_running = True
        self.file_monitoring_active = True
        self.processing_active = True
        self.rag_active = True
        
        # Processing queue
        self.processing_queue = queue.Queue()
        
        # Statistics
        self.stats = {
            'logs_analyzed': 0,
            'vectors_stored': 0,
            'errors_skipped': 0,
            'retries_attempted': 0,
            'rate_limits_hit': 0,
            'auth_failures': 0,
            'processing_method': 'unknown',  # Track which method was used
            'files_processed': 0
        }
    
    def setup_environment(self):
        """Setup environment quickly"""
        print("🚀 Setting up parallel CI/CD environment...")
        
        try:
            creator = DemoFolderCreator()
            creator.create_complete_structure()
            
            es_setup = ElasticsearchSetup()
            es_setup.create_all_indexes()
            
            print("✅ Environment ready for parallel processing!")
            return True
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def wait_for_services(self):
        """Quick service check"""
        print("⏳ Checking services...")
        
        for attempt in range(10):
            all_ready = True
            for service_name, url in self.service_urls.items():
                try:
                    response = requests.get(f"{url}/health", timeout=300)
                    print(response, response.status_code, response.text)
                    if response.status_code != 200:
                        print(f"🔑 Azure OpenAI service not ready: {response.text}")
                        all_ready = False
                        break
                except Exception as e:
                    print(f"❌ {service_name} not ready: {e}")
                    all_ready = False
                    break
            
            if all_ready:
                print("✅ All services ready!")
                return True
            
            print(f"⏳ Waiting... (attempt {attempt + 1}/10)")
            time.sleep(5)
        
        return False
    
    def parallel_file_monitoring(self):
        """Parallel process 1: Continuous file monitoring and DB storage"""
        print("📁 Starting parallel file monitoring...")
        
        while self.file_monitoring_active and self.system_running:
            try:
                # Check for new files
                scan_response = requests.post(f"{self.service_urls['folder_scanner']}/scan", timeout=30)
                
                if scan_response.status_code == 200:
                    result = scan_response.json()
                    files_stored = result.get('files_stored', 0)
                    
                    if files_stored > 0:
                        self.stats['files_processed'] += files_stored
                        print(f"📁 File Monitor: {files_stored} new files stored (Total: {self.stats['files_processed']})")
                    
                    # Add unprocessed logs to queue
                    self.queue_unprocessed_logs()
                    
                else:
                    print(f"📁 File Monitor: Scan failed ({scan_response.status_code})")
                
                # Wait 2 minutes before next scan
                time.sleep(3600)
                
            except Exception as e:
                print(f"📁 File Monitor Error: {e}")
                time.sleep(60)
    
    def queue_unprocessed_logs(self):
        """Add unprocessed logs to processing queue"""
        try:
            logs_response = requests.get(f"{self.service_urls['db_service']}/get-unprocessed-logs", timeout=120)
            
            if logs_response.status_code == 200:
                unprocessed_logs = logs_response.json().get('logs', [])
                
                for log_item in unprocessed_logs:
                    if not self.processing_queue.full():
                        self.processing_queue.put(log_item)
                
                if unprocessed_logs:
                    print(f"📋 Queue: Added {len(unprocessed_logs)} logs to processing queue")
                    
        except Exception as e:
            print(f"📋 Queue Error: {e}")
    
    def parallel_log_processing(self):
        """Parallel process 2: Continuous log processing with flexible input"""
        print("🔄 Starting parallel log processing...")
        
        def process_log_worker():
            """Worker thread for processing logs"""
            while self.processing_active and self.system_running:
                try:
                    # Get log from queue (wait up to 30 seconds)
                    log_item = self.processing_queue.get(timeout=3000)
                    
                    time.sleep(0.1)
                    # Process with flexible input handling
                    success = self.process_single_log_flexible(log_item)
                    
                    if success:
                        self.stats['logs_analyzed'] += 1
                        print(f"🔄 Processor: Log analyzed (Total: {self.stats['logs_analyzed']})")
                    else:
                        self.stats['errors_skipped'] += 1
                        print(f"⏭️ Processor: Skipped invalid input (Total skipped: {self.stats['errors_skipped']})")
                    
                    self.processing_queue.task_done()
                    
                except queue.Empty:
                    # No logs in queue, continue waiting
                    continue
                except Exception as e:
                    print(f"🔄 Processor Error: {e}")
                    time.sleep(5)
        
        # Start multiple worker threads
        for i in range(3):  # 3 parallel workers
            worker_thread = threading.Thread(target=process_log_worker)
            worker_thread.daemon = True
            worker_thread.start()
            print(f"🔄 Started processor worker {i+1}")

    def process_single_log_flexible(self, log_item, max_retries=3):
        """Process single log with flexible input handling and retry logic"""
        
        for attempt in range(max_retries):
            try:
                log_data = log_item.get('data', {})
                
                # Flexible input validation - skip if essential data missing
                if not log_data.get('log_content') or not log_item.get('log_id'):
                    print(f"⏭️ Skipping log: Missing essential data")
                    return False
                
                # Prepare flexible analysis data
                analysis_data = {
                    "content": log_data.get('log_content', ''),
                    "metadata": {
                        "log_id": log_item.get('log_id'),
                        "correlation_id": log_data.get('correlation_id', 'unknown'),
                        "tool": log_data.get('tool', 'unknown'),
                        "project": log_data.get('project', 'unknown'),
                        "environment": log_data.get('environment', 'unknown'),
                        "server": log_data.get('server', 'unknown'),
                        "log_type": log_data.get('log_type', 'unknown'),
                        "status": log_data.get('status', 'unknown')
                    }
                }
                
                # Send to LLM with retry logic
                llm_response = requests.post(
                    f"{self.service_urls['llm_analysis']}/analyze",
                    json=analysis_data,
                    timeout=120  # 2 minutes timeout
                )
                
                if llm_response.status_code == 200:
                    try:
                        response_data = llm_response.json()
                        if response_data.get('status') == 'success':
                            self.stats['vectors_stored'] += 1
                            print(f"✅ Log {log_item.get('log_id')} processed successfully")
                            return True
                    except json.JSONDecodeError:
                        print(f"⚠️ Non-JSON response but processing succeeded for log {log_item.get('log_id')}")
                        return True
                        
                elif llm_response.status_code == 401:
                    print(f"🔑 CRITICAL: Azure OpenAI Authentication failed - check API key")
                    raise Exception("Azure OpenAI authentication failed - stopping processing")
                    
                elif llm_response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"⏰ Rate limit hit - retry {attempt + 1}/{max_retries} in {wait_time}s")
                    time.sleep(wait_time)
                    continue  # Retry the request
                    
                else:
                    print(f"❌ HTTP {llm_response.status_code} for log {log_item.get('log_id')}")
                    return False
                    
            except requests.exceptions.Timeout:
                print(f"⏰ Timeout on attempt {attempt + 1}/{max_retries} for log {log_item.get('log_id')}")
                if attempt == max_retries - 1:
                    return False
                time.sleep(1)
                continue
                
            except requests.exceptions.ConnectionError as e:
                print(f"🔌 Connection error on attempt {attempt + 1}/{max_retries}: {str(e)[:100]}")
                if attempt == max_retries - 1:
                    return False
                time.sleep(2)
                continue
                
            except Exception as e:
                print(f"⏭️ Error processing log {log_item.get('log_id')}: {str(e)[:100]}")
                return False
        
        # If we get here, all retries failed
        print(f"❌ All {max_retries} attempts failed for log {log_item.get('log_id')}")
        self.stats['errors_skipped'] += 1
        return False
 
    def trigger_continuous_processing(self):
        """Trigger continuous processing of all unprocessed logs"""
        try:
            print("🚀 Starting continuous processing of all logs...")
            
            # Check if LLM service is ready first
            try:
                health_check = requests.get(f"{self.service_urls['llm_analysis']}/health", timeout=10)
                print(f"🔍 LLM service health: {health_check.status_code}")
                if health_check.status_code != 200:
                    print(f"❌ LLM service not healthy: {health_check.text}")
                    return False
            except Exception as health_error:
                print(f"❌ LLM service health check failed: {health_error}")
                return False
        
        
            response = requests.post(
                f"{self.service_urls['llm_analysis']}/process-all-continuous",
                timeout=600  # 10 minutes timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                total_processed = result.get('results', {}).get('total_processed', 0)
                total_errors = result.get('results', {}).get('total_errors', 0)
                total_batches = result.get('results', {}).get('batches_processed', 0)
                
                print(f"✅ Continuous processing completed!")
                print(f"📊 Total processed: {total_processed}")
                print(f"❌ Total errors: {total_errors}")
                print(f"📦 Total batches: {total_batches}")
                
                # Update your existing stats
                self.stats['logs_analyzed'] = total_processed
                self.stats['errors_skipped'] = total_errors
                self.stats['vectors_stored'] = total_processed  # Assuming successful processing stores vectors
                
                return True
            else:
                print(f"❌ Continuous processing failed: HTTP {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"⏰ Continuous processing timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"❌ Error triggering continuous processing: {e}")
            return False
    
    def run_processing_with_continuous_option(self):
        """Process logs individually as they become available"""
        print("🔄 Starting individual log processing...")
        
        # Start the parallel processing workers
        self.parallel_log_processing()
        
        # Keep processing until no more logs or system stops
        processed_count = 0
        while self.processing_active and self.system_running:
            try:
                # Queue unprocessed logs
                self.queue_unprocessed_logs()
                
                # Check if we've processed any logs
                if self.stats['logs_analyzed'] > processed_count:
                    processed_count = self.stats['logs_analyzed']
                    print(f"📊 Progress: {processed_count} logs analyzed")
                
                # Wait before checking again
                time.sleep(10)
                
                # Check if queue is empty and no new logs
                if self.processing_queue.empty():
                    # Check for new unprocessed logs
                    logs_response = requests.get(f"{self.service_urls['db_service']}/get-unprocessed-logs", timeout=30)
                    if logs_response.status_code == 200:
                        unprocessed = logs_response.json().get('logs', [])
                        if not unprocessed:
                            print("✅ No more unprocessed logs - processing complete!")
                            break
                            
            except Exception as e:
                print(f"❌ Error in processing loop: {e}")
                time.sleep(5)
        
        # Stop processing
        self.processing_active = False
        print(f"🎯 Individual processing completed! Total analyzed: {self.stats['logs_analyzed']}")
        return True

    def parallel_rag_chatbot(self):
        """Parallel process 3: Keep RAG chatbot online and responsive"""
        print("🤖 Starting parallel RAG chatbot monitoring...")
        
        while self.rag_active and self.system_running:
            try:
                # Check RAG health
                rag_response = requests.get(f"{self.service_urls['rag_chatbot']}/health", timeout=1000)
                
                if rag_response.status_code == 200:
                    # RAG is healthy - could add auto-testing here
                    pass
                else:
                    print(f"🤖 RAG Health Warning: Status {rag_response.status_code}")
                
                # Wait 60 seconds before next check
                time.sleep(60)
                
            except Exception as e:
                print(f"🤖 RAG Monitor Error: {e}")
                time.sleep(60)
    
    def parallel_system_monitoring(self):
        """Parallel process 4: System monitoring and statistics"""
        print("📊 Starting parallel system monitoring...")
        
        while self.system_running:
            try:
                # Get database stats
                stats_response = requests.get(f"{self.service_urls['db_service']}/stats", timeout=1500)
                
                if stats_response.status_code == 200:
                    db_stats = stats_response.json()
                    
                    current_time = datetime.now().strftime('%H:%M:%S')
                    print(f"\n📊 Parallel System Status [{current_time}]:")
                    print(f"   📁 Files processed: {self.stats['files_processed']}")
                    print(f"   🔄 Logs analyzed: {self.stats['logs_analyzed']}")
                    print(f"   🔍 Vectors stored: {self.stats['vectors_stored']}")
                    print(f"   ⏭️ Errors skipped: {self.stats['errors_skipped']}")
                    print(f"   📋 Queue size: {self.processing_queue.qsize()}")
                    print(f"   📄 DB Total logs: {db_stats.get('total_logs', 0)}")
                    print(f"   ✅ DB Processed: {db_stats.get('processed_logs', 0)}")
                    print(f"   🧠 DB Analyses: {db_stats.get('total_analyses', 0)}")
                    print(f"   🔍 DB Vectors: {db_stats.get('total_vectors', 0)}")
                    
                    # Status indicators
                    print(f"   📁 File Monitor: {'🟢 Active' if self.file_monitoring_active else '🔴 Stopped'}")
                    print(f"   🔄 Log Processor: {'🟢 Active' if self.processing_active else '🔴 Stopped'}")
                    print(f"   🤖 RAG Chatbot: {'🟢 Online' if self.rag_active else '🔴 Offline'}")
                
                # Monitor every 90 seconds
                time.sleep(90)
                
            except Exception as e:
                print(f"📊 Monitor Error: {e}")
                time.sleep(90)

    def main(self):
        """Main execution method"""
        print("🚀 Starting CICD Log Analysis System")
        
        if not self.setup_environment():
            print("❌ Environment setup failed")
            return
        
        if not self.wait_for_services():
            print("❌ Services not ready - cannot start processing")
            return
        
        print("✅ All services are ready")
        
        # ✅ Step 1: Trigger folder scanning first
        print("📁 Step 1: Scanning for new log files...")
        try:
            scan_response = requests.post(f"{self.service_urls['folder_scanner']}/scan", timeout=60000)
            if scan_response.status_code == 200:
                scan_result = scan_response.json()
                files_stored = scan_result.get('files_stored', 0)
                print(f"📁 Folder scan completed: {files_stored} new files stored")
                
                if files_stored == 0:
                    print("ℹ️  No new files found to process")
                    return
            else:
                print(f"❌ Folder scan failed: {scan_response.status_code}")
                return
        except Exception as e:
            print(f"❌ Error triggering folder scan: {e}")
            return
        
        # ✅ Step 2: Process the scanned logs
        print("🔄 Step 2: Starting log analysis...")
        success = self.run_processing_with_continuous_option()
        
        if success:
            print("🎯 All logs processed successfully!")
            self.print_final_stats()
        else:
            print("❌ Processing failed")


    def print_final_stats(self):
        """Print final processing statistics"""
        print("\n" + "="*50)
        print("📊 FINAL PROCESSING STATISTICS")
        print("="*50)
        print(f"📈 Logs analyzed: {self.stats['logs_analyzed']}")
        print(f"💾 Vectors stored: {self.stats['vectors_stored']}")
        print(f"❌ Errors skipped: {self.stats['errors_skipped']}")
        print(f"🔄 Retries attempted: {self.stats['retries_attempted']}")
        print(f"⏰ Rate limits hit: {self.stats['rate_limits_hit']}")
        print(f"🔑 Auth failures: {self.stats['auth_failures']}")
        print(f"📋 Processing method: {self.stats['processing_method']}")
        print("="*50)



if __name__ == "__main__":
    analyzer = ParallelCICDAnalyzer()
    analyzer.main()
