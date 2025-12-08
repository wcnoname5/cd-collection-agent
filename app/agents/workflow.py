import os
from langgraph.graph import StateGraph, END
from typing import TypedDict

# TODO:LLM support would be implement latter.
# Optional backends: prefer Ollama if available, otherwise Transformers (GPT-2 by default).
# You can override with env vars: LLM_BACKEND=('ollama'|'transformers'|'auto'), LLM_MODEL, TRANSFORMERS_MODEL

# Try to import Ollama Python client if it's installed. If not available we'll fall back.
try:
    import ollama  # type: ignore
    _OLLAMA_AVAILABLE = True
except Exception:
    ollama = None
    _OLLAMA_AVAILABLE = False

class ChatState(TypedDict):
    user_input: str
    model_output: str

# --- The LLM chat Node ---
def llm_chat_node(state: ChatState):
    """
    Interacts with a local model running via Ollama.
    Assumes Ollama is running (e.g., via the desktop app or terminal).
    """
    user_input = state["user_input"]
    
    # Decide backend: explicit env var or auto-detect
    backend = os.getenv("LLM_BACKEND", "auto").lower()
    model_env = os.getenv("LLM_MODEL")

    # Ollama path
    if backend == "ollama" or (backend == "auto" and _OLLAMA_AVAILABLE):
        MODEL_NAME = model_env or os.getenv("OLLAMA_MODEL", "gemma:2b")
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": user_input}],
            )

            output = response.get("message", {}).get("content")
            return {"model_output": output}

        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return {"model_output": f"Error: Could not connect to Ollama or model '{MODEL_NAME}' is not available."}

    # Transformers (fallback)
    else:
        TRANSFORMERS_MODEL = model_env or os.getenv("TRANSFORMERS_MODEL", "gpt2")

        # Lazy-load the generator to avoid heavy imports at module import time
        if not hasattr(llm_chat_node, "_generator"):
            try:
                from transformers import pipeline

                # Create a text-generation pipeline. Adjust params as needed.
                llm_chat_node._generator = pipeline(
                    "text-generation", model=TRANSFORMERS_MODEL
                )
            except Exception as e:
                print(f"Error initializing transformers pipeline: {e}")
                return {"model_output": "Error: transformers pipeline could not be initialized. Install 'transformers' and a model."}

        try:
            out = llm_chat_node._generator(user_input, max_length=256, do_sample=True, top_p=0.95, num_return_sequences=1)
            # The pipeline returns a list of dicts with 'generated_text'
            output = out[0].get("generated_text") if isinstance(out, list) and out else str(out)
            return {"model_output": output}
        except Exception as e:
            print(f"Error running transformers generator: {e}")
            return {"model_output": "Error: generation failed using transformers backend."}

def build_workflow():
    graph = StateGraph(ChatState)
    graph.add_node("llm_chat", llm_chat_node)
    graph.set_entry_point("llm_chat")
    graph.add_edge("llm_chat", END)
    return graph.compile()

# Backwards-compatible wrapper: some versions of the compiled StateGraph
# expose different call names (invoke / run / __call__). Consumers in
# this repo expect `workflow.invoke(...)`. Wrap the compiled graph so
# that `invoke` will try common call methods.
class WorkflowInvoker:
    def __init__(self, compiled):
        self._compiled = compiled

    def invoke(self, state: ChatState):
        # Try a sequence of possible call targets returning the node output dict
        target = self._compiled

        # If the compiled object already has an invoke, just call it
        if hasattr(target, "invoke"):
            return target.invoke(state)

        # Common alternative names
        for name in ("run", "execute"):
            fn = getattr(target, name, None)
            if callable(fn):
                return fn(state)

        # If the compiled object itself is callable, call it
        if callable(target):
            return target(state)

        # Nothing worked — raise informative error
        raise AttributeError(
            "Compiled workflow does not expose a callable interface (tried: invoke, run, execute, __call__)."
        )


workflow = WorkflowInvoker(build_workflow())
