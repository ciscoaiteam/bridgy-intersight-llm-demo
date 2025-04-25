from langchain_ollama import OllamaLLM  # Updated import
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from .intersight_expert import IntersightExpert
from .ai_pods_expert import AIPodExpert
from .general_expert import GeneralExpert
import logging
from config import setup_langsmith

logger = logging.getLogger(__name__)

# Initialize LangSmith
setup_langsmith()

class ExpertRouter:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key = "LLM",
            model="/ai/models/Meta-Llama-3-8B-Instruct/", 
            base_url = "http://64.101.169.102:8000/v1",
            temperature=0.0
        )

        # Initialize experts
        self.experts = {
            "intersight": IntersightExpert(),
            "ai_pods": AIPodExpert(),
            "general": GeneralExpert()
        }

        # Router prompt template
        self.router_prompt = ChatPromptTemplate.from_template("""
        You are an expert router for Cisco infrastructure questions. Analyze the question and determine which expert should handle it:

        1. Intersight Expert: For questions about:
           - Server inventory, status, and configuration (e.g., "What servers do I have?", "What's running in my environment?")
           - Infrastructure management and monitoring
           - Hardware details and specifications
           - Cisco Intersight API and platform features
           - ANY questions about current servers, network elements, or physical devices in the user's environment
        2. AI Pods Expert: For questions about:
           - Cisco AI Pods, their documentation, and implementation
           - LLM models and their hardware requirements
           - Machine learning infrastructure sizing
           - AI inference and training hardware
           - Any mention of LLM sizes like 7B, 13B, 40B, 70B, etc.
        3. General Expert: For general Cisco knowledge questions that don't relate to specific infrastructure

        Question: {question}

        Respond with just the expert name: "intersight", "ai_pods", or "general"
        """)

        # Create router chain using the new RunnableSequence pattern
        self.router_chain = self.router_prompt | self.llm

    def route_and_respond(self, query: str) -> tuple[str, str]:
        try:
            logger.info("Using chain of thought to determine expert")
            expert_choice = self._determine_expert_with_cot(query)
            logger.info(f"Chain of thought selected: {expert_choice}")

            if expert_choice == "intersight":
                try:
                    logger.info("Routing to Intersight Expert")
                    return self.experts["intersight"].get_response(query), "Intersight Expert"
                except Exception as e:
                    logger.error(f"Intersight Expert error: {str(e)}")
                    try:
                        logger.info("Falling back to General Expert due to Intersight error")
                        fallback_response = self.experts["general"].get_response(
                            f"The user asked '{query}' about Intersight, but I couldn't access the Intersight API. Please provide a general answer."
                        )
                        return f"Note: Could not connect to Intersight API. Using general knowledge instead.\n\n{fallback_response}", "General Expert (Fallback)"
                    except Exception as fallback_error:
                        logger.error(f"Fallback expert error: {str(fallback_error)}")
                        return f"I'm sorry, I encountered an error: {str(e)}", "System"

            elif expert_choice == "ai_pods":
                try:
                    logger.info("Routing to AI Pods Expert")
                    return self.experts["ai_pods"].get_response(query), "AI Pods Expert"
                except Exception as e:
                    logger.error(f"AI Pods Expert error: {str(e)}")
                    return f"AI Pods Expert Error: {str(e)}", "System"

            else:
                try:
                    logger.info("Routing to General Expert")
                    return self.experts["general"].get_response(query), "General Expert"
                except Exception as e:
                    logger.error(f"General Expert error: {str(e)}")
                    return f"General Expert Error: {str(e)}", "System"

        except Exception as routing_error:
            logger.error(f"Error in routing logic: {str(routing_error)}")
            return self._basic_routing_fallback(query)

    def _determine_expert_with_cot(self, query: str) -> str:
        try:
            response = self.router_chain.invoke({"question": query})
            expert_choice = response.strip().lower()
            logger.debug(f"Router chain response: {expert_choice}")

            if expert_choice in ["intersight", "ai_pods", "general"]:
                return expert_choice

            last_words = expert_choice.split()[-5:]
            if "intersight" in last_words:
                return "intersight"
            elif "ai_pods" in last_words or "ai pods" in ' '.join(last_words):
                return "ai_pods"
            elif "general" in last_words:
                return "general"

            if self._is_server_inventory_query(query):
                logger.info("Detected server inventory query via semantic detection")
                return "intersight"

            return "general"

        except Exception as e:
            logger.error(f"Error in chain of thought: {str(e)}")
            if "intersight" in query.lower() or any(word in query.lower() for word in ["server", "servers", "hardware", "datacenter"]):
                return "intersight"
            elif "ai pods" in query.lower():
                return "ai_pods"
            else:
                return "general"

    def _basic_routing_fallback(self, query: str) -> tuple[str, str]:
        if self._is_intersight_query(query):
            try:
                return self.experts["intersight"].get_response(query), "Intersight Expert"
            except Exception as e:
                logger.error(f"Fallback intersight expert error: {str(e)}")
                try:
                    fallback_response = self.experts["general"].get_response(
                        f"The user asked '{query}' about Intersight, but I couldn't access the Intersight API. Please provide a general answer."
                    )
                    return f"Note: Could not connect to Intersight API. Using general knowledge instead.\n\n{fallback_response}", "General Expert (Fallback)"
                except:
                    return "I'm sorry, I encountered multiple errors trying to process your request.", "System"
        elif self._is_ai_pods_query(query):
            try:
                return self.experts["ai_pods"].get_response(query), "AI Pods Expert"
            except:
                return "I'm sorry, I encountered an error with the AI Pods expert.", "System"
        else:
            try:
                return self.experts["general"].get_response(query), "General Expert"
            except:
                return "I'm sorry, I encountered an error processing your request.", "System"

    def _is_intersight_query(self, query: str) -> bool:
        query_lower = query.lower().strip()

        if self._is_server_inventory_query(query):
            return True

        environment_context = [
            "environment" in query_lower and not query_lower.startswith("what is"),
            "my" in query_lower and ("servers" in query_lower or "infrastructure" in query_lower),
            "running" in query_lower and not query_lower.startswith("how"),
            "status" in query_lower and "server" in query_lower,
            "health" in query_lower and "infrastructure" in query_lower
        ]

        if any(environment_context):
            return True

        intersight_keywords = [
            "intersight", "server", "servers", "ucs", "hardware", "compute", 
            "blade", "rack", "infrastructure", "inventory", "datacenter"
        ]
        if any(keyword in query_lower for keyword in intersight_keywords):
            general_knowledge_indicators = ["what is", "how does", "explain", "tell me about"]
            if not any(indicator in query_lower for indicator in general_knowledge_indicators):
                return True

        return False

    def _is_ai_pods_query(self, query: str) -> bool:
        query_lower = query.lower()

        llm_size_patterns = [
            "7b", "7 b", "13b", "13 b", "40b", "40 b", "70b", "70 b",
            "billion parameter", "billion parameters", "b model", "b llm"
        ]
        if any(size_pattern in query_lower for size_pattern in llm_size_patterns):
            return True

        general_knowledge_indicators = [
            "why is", "what is", "how does", "explain", 
            "tell me about", "describe", "definition of"
        ]

        if any(indicator in query_lower for indicator in general_knowledge_indicators):
            if any(cisco_term in query_lower for cisco_term in ["cisco", "ai pod", "ai pods", "llm", "large language model"]):
                return True
            else:
                ai_hardware_terms = ["hardware for llm", "gpu for llm", "infrastructure for llm", "server for ai"]
                if any(term in query_lower for term in ai_hardware_terms):
                    return True
                return False

        ai_pods_keywords = [
            "ai pods", "ai pod", "aipod", "aipods", 
            "llm", "large language model", "ml model",
            "machine learning", "deep learning", "neural network",
            "gpu cluster", "ai infrastructure", "ml infrastructure",
            "ai compute", "ml compute", "inference", 
            "gpu for", "hardware for", "server for ai", "hardware recommendation",
            "what should i buy", "which pod", "recommendation for llm"
        ]
        return any(keyword in query_lower for keyword in ai_pods_keywords)

    def _is_server_inventory_query(self, query: str) -> bool:
        query = query.lower().strip()

        environment_patterns = [
            query.startswith("what") and ("environment" in query or "servers" in query),
            "running in " in query and ("environment" in query or "my" in query),
            "servers do i have" in query,
            "in my environment" in query,
            "show" in query and ("servers" in query or "infrastructure" in query),
            "list" in query and ("servers" in query or "infrastructure" in query),
            "what's" in query and "running" in query,
            "what is" in query and "running" in query,
            "deployed" in query and "servers" in query
        ]

        return any(environment_patterns)
