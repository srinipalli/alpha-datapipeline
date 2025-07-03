# services/rag_chatbot_service.py - RAG chatbot with memory (using your template)
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from langchain_community.llms import Ollama
import uuid
import json
import base64
from datetime import datetime
import re
from typing import List, Dict

app = Flask(__name__)
CORS(app)

class CICDRagChatbot:
    def __init__(self):
        # Decode your API key
        api_key_decoded = base64.b64decode("bFBtMm1KY0JZeEpjNHpvYjVySkM6eVE3bUlNTWJqNjhvU1ZIWjBGSE9QUQ==").decode('utf-8')
        key_parts = api_key_decoded.split(':')
        
        self.es = Elasticsearch(
            ["https://a774a75424564c46a6264388ef74dcd6.us-central1.gcp.cloud.es.io:443"],
            api_key=(key_parts[0], key_parts[1]),
            verify_certs=True,
            request_timeout=60
        )
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.llm = Ollama(
            model="llama3.1:8b",
            temperature=0.3,
            top_p=0.9,
            num_ctx=4096,
            num_predict=1000,
            repeat_penalty=1.1
        )
        
        self.vector_index = "cicd_vectors"
        self.memory_index = "cicd_chat_memory"
        
        print("✅ CI/CD RAG Chatbot initialized successfully")
    
    def extract_intent_and_entities(self, user_message: str) -> tuple:
        """Extract intent and entities from user message"""
        intents = {
            "error_diagnosis": ["error", "failed", "issue", "problem", "broken", "crash", "failing"],
            "solution_request": ["how to", "fix", "solve", "resolve", "help", "repair", "troubleshoot"],
            "command_request": ["command", "script", "run", "execute", "cli", "terminal"],
            "explanation_request": ["what is", "explain", "why", "how does", "what does", "meaning"],
            "deployment_help": ["deploy", "deployment", "release", "rollback", "revert"],
            "build_help": ["build", "compile", "package", "bundle", "npm", "docker", "maven"]
        }
        
        entities = {
            "technologies": ["docker", "kubernetes", "k8s", "jenkins", "github", "gitlab", "terraform", "npm", "node", "python", "java", "maven", "gradle"],
            "stages": ["build", "test", "deploy", "release", "infrastructure", "staging", "production"],
            "error_types": ["timeout", "permission", "network", "authentication", "syntax", "memory", "disk", "connection"]
        }
        
        detected_intent = "general"
        detected_entities = []
        
        message_lower = user_message.lower()
        
        # Detect intent
        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_intent = intent
                break
        
        # Detect entities
        for entity_type, values in entities.items():
            for value in values:
                if value in message_lower:
                    detected_entities.append({"type": entity_type, "value": value})
        
        return detected_intent, detected_entities
    
    def get_chat_memory(self, session_id: str, limit: int = 6) -> List[Dict]:
        """Retrieve chat memory for session"""
        try:
            response = self.es.search(
                index=self.memory_index,
                body={
                    "query": {"term": {"session_id": session_id}},
                    "sort": [{"last_updated": {"order": "desc"}}],
                    "size": 1
                }
            )
            
            if response['hits']['hits']:
                memory_doc = response['hits']['hits'][0]['_source']
                conversations = memory_doc.get('conversation_history', [])
                return conversations[-limit:] if len(conversations) > limit else conversations
            
            return []
        except Exception as e:
            print(f"Error retrieving memory: {e}")
            return []
    
    def update_chat_memory(self, session_id: str, user_id: str, user_message: str, bot_response: str, intent: str, entities: List[Dict]):
        """Update chat memory with new conversation"""
        try:
            existing_memory = self.es.search(
                index=self.memory_index,
                body={"query": {"term": {"session_id": session_id}}}
            )
            
            new_user_message = {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.utcnow().isoformat(),
                "intent": intent
            }
            
            new_bot_message = {
                "role": "assistant",
                "content": bot_response,
                "timestamp": datetime.utcnow().isoformat(),
                "intent": "response"
            }
            
            if existing_memory['hits']['hits']:
                # Update existing memory
                doc_id = existing_memory['hits']['hits'][0]['_id']
                existing_doc = existing_memory['hits']['hits'][0]['_source']
                
                conversation_history = existing_doc.get('conversation_history', [])
                conversation_history.extend([new_user_message, new_bot_message])
                
                # Keep only last 20 conversations for efficiency
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
                
                # Generate context summary
                context_summary = self._generate_context_summary(conversation_history)
                
                update_doc = {
                    "conversation_history": conversation_history,
                    "context_summary": context_summary,
                    "last_updated": datetime.utcnow().isoformat(),
                    "message_count": len(conversation_history)
                }
                
                self.es.update(
                    index=self.memory_index,
                    id=doc_id,
                    body={"doc": update_doc}
                )
            else:
                # Create new memory document
                memory_doc = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "conversation_history": [new_user_message, new_bot_message],
                    "context_summary": f"User discussing CI/CD issues with intent: {intent}",
                    "last_updated": datetime.utcnow().isoformat(),
                    "message_count": 2
                }
                
                self.es.index(
                    index=self.memory_index,
                    body=memory_doc
                )
                
        except Exception as e:
            print(f"Error updating memory: {e}")
    
    def _generate_context_summary(self, conversation_history: List[Dict]) -> str:
        """Generate summary of conversation context"""
        if len(conversation_history) < 4:
            return "Recent conversation about CI/CD issues"
        
        # Get last few user messages for summary
        user_messages = [conv['content'] for conv in conversation_history if conv['role'] == 'user']
        recent_messages = user_messages[-3:]
        
        summary_prompt = f"""Summarize the main CI/CD topics discussed in these messages in 1-2 sentences:

Messages:
{chr(10).join(recent_messages)}

Summary:"""
        
        try:
            summary = self.llm.invoke(summary_prompt)
            return summary.strip()[:200]
        except:
            return "Discussion about CI/CD pipeline issues and troubleshooting"
    
    def retrieve_relevant_knowledge(self, query: str, conversation_context: str = "", top_k: int = 3) -> List[Dict]:
        """Retrieve relevant knowledge from vector database"""
        try:
            # Combine query with conversation context
            combined_query = f"{conversation_context} {query}" if conversation_context else query
            query_embedding = self.embedding_model.encode(combined_query).tolist()
            
            # Hybrid search: vector + keyword
            search_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'content_vector') + 1.0",
                                        "params": {"query_vector": query_embedding}
                                    }
                                }
                            },
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["content^2", "tool", "project", "environment", "log_type"],
                                    "boost": 0.5
                                }
                            }
                        ]
                    }
                },
                "_source": ["content", "tool", "project", "environment", "log_type", "status", "solution_type", "tags"]
            }
            
            response = self.es.search(index=self.vector_index, body=search_body)
            
            relevant_docs = []
            for hit in response['hits']['hits']:
                doc = hit['_source']
                doc['relevance_score'] = hit['_score']
                relevant_docs.append(doc)
            
            return relevant_docs
            
        except Exception as e:
            print(f"Error retrieving knowledge: {e}")
            return []
    
    def generate_response(self, user_message: str, session_id: str, user_id: str = "default_user") -> Dict:
        """Generate RAG response with memory using Llama 3.1 8B"""
        try:
            # Extract intent and entities
            intent, entities = self.extract_intent_and_entities(user_message)
            
            # Get conversation memory
            conversation_history = self.get_chat_memory(session_id)
            
            # Create conversation context
            context_messages = []
            if conversation_history:
                for conv in conversation_history[-4:]:  # Last 2 exchanges
                    context_messages.append(f"{conv['role']}: {conv['content']}")
                conversation_context = "\n".join(context_messages)
            else:
                conversation_context = ""
            
            # Retrieve relevant knowledge from processed logs
            relevant_docs = self.retrieve_relevant_knowledge(user_message, conversation_context)
            
            # Prepare knowledge context from analyzed logs
            knowledge_context = ""
            if relevant_docs:
                knowledge_context = "\n\n".join([
                    f"Analyzed Log {i+1}:\n"
                    f"Tool: {doc['tool']}\n"
                    f"Project: {doc['project']}\n"
                    f"Environment: {doc['environment']}\n"
                    f"Log Type: {doc['log_type']}\n"
                    f"Status: {doc['status']}\n"
                    f"Analysis: {doc['content']}"
                    for i, doc in enumerate(relevant_docs)
                ])
            
            # Create optimized prompt for Llama 3.1 8B
            llama31_prompt = f"""You are an expert CI/CD DevOps assistant with access to analyzed log data from various CI/CD tools. Help troubleshoot CI/CD pipeline issues with specific, actionable solutions.

CONVERSATION HISTORY:
{conversation_context}

RELEVANT ANALYZED LOGS:
{knowledge_context}

USER INTENT: {intent}
DETECTED TECHNOLOGIES: {', '.join([e['value'] for e in entities if e['type'] == 'technologies'])}

USER QUESTION: {user_message}

INSTRUCTIONS:
1. Provide specific, actionable solutions for CI/CD issues based on analyzed log data
2. Include exact commands and code examples when relevant
3. Reference conversation history if applicable
4. Focus on practical implementation steps based on similar analyzed cases
5. If unsure, ask clarifying questions
6. Be concise but thorough
7. Use insights from the analyzed logs to provide better recommendations

RESPONSE:"""

            # Generate response using Llama 3.1 8B
            response = self.llm.invoke(llama31_prompt)
            bot_response = response.strip()
            
            # Update chat memory
            self.update_chat_memory(session_id, user_id, user_message, bot_response, intent, entities)
            
            return {
                "response": bot_response,
                "intent": intent,
                "entities": entities,
                "relevant_knowledge": len(relevant_docs),
                "session_id": session_id,
                "model": "llama3.1:8b",
                "knowledge_sources": [f"{doc['tool']}-{doc['log_type']}" for doc in relevant_docs]
            }
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again or rephrase your question.",
                "intent": "error",
                "entities": [],
                "relevant_knowledge": 0,
                "session_id": session_id,
                "model": "llama3.1:8b"
            }

chatbot = CICDRagChatbot()

@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        user_id = data.get('user_id', 'default_user')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Generate response
        response = chatbot.generate_response(user_message, session_id, user_id)
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for session"""
    try:
        history = chatbot.get_chat_memory(session_id, limit=20)
        return jsonify({'history': history}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """Streaming chat endpoint for real-time interaction"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        def generate_streaming_response():
            # Get relevant knowledge
            relevant_docs = chatbot.retrieve_relevant_knowledge(user_message)
            
            # Prepare context
            knowledge_context = ""
            if relevant_docs:
                knowledge_context = "\n\n".join([
                    f"Log Analysis {i+1}:\n"
                    f"Tool: {doc['tool']}\n"
                    f"Type: {doc['log_type']}\n"
                    f"Status: {doc['status']}\n"
                    f"Analysis: {doc['content'][:200]}..."
                    for i, doc in enumerate(relevant_docs)
                ])
            
            # Stream response
            yield f"data: {json.dumps({'type': 'knowledge', 'count': len(relevant_docs)})}\n\n"
            
            # Generate response
            response = chatbot.generate_response(user_message, session_id)
            
            yield f"data: {json.dumps({'type': 'response', 'content': response['response']})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
        
        return Response(generate_streaming_response(), mimetype='text/plain')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test Elasticsearch connection
        es_health = chatbot.es.ping()
        
        # Test Llama 3.1 connection (quick test)
        try:
            llama_test = chatbot.llm.invoke("Hello")
            llama_health = len(llama_test) > 0
        except:
            llama_health = False
        
        return jsonify({
            'status': 'healthy',
            'service': 'rag_chatbot',
            'elasticsearch': es_health,
            'llama31': llama_health,
            'model': 'llama3.1:8b',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy', 
            'error': str(e),
            'service': 'rag_chatbot'
        }), 500
if __name__ == '__main__':
    print("🚀 Starting CI/CD RAG Chatbot with Llama 3.1 8B...")
    print("🦙 Model: Llama 3.1 8B via Ollama")
    print("🔍 Features: ELK Vector DB, Chat Memory, Analyzed Log Knowledge")
    app.run(debug=False, port=5004, use_reloader=False)
