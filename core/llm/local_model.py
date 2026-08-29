import logging
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from core.config import Config

logger = logging.getLogger(__name__)

class LocalLLM:
    def __init__(self):
        self.model_name = Config.LLM_MODEL_NAME
        self.device = Config.DEVICE
        self.model = None
        self.tokenizer = None
        self.loaded = False
        self.context_length = 128000  # LFM2.5 supports 128K context

    def load(self):
        try:
            logger.info(f"Loading Liquid AI model {self.model_name} on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                use_fast=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True
            )
            self.model.to(self.device)
            if hasattr(self.model, "enable_agentic_mode"):
                self.model.enable_agentic_mode()
            self.loaded = True
            logger.info("✅ Liquid AI model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Model load error: {e}")
            return False

    def generate(self, prompt, max_new_tokens=512, temperature=0.7, tools=None):
        if not self.loaded:
            return "Model not loaded."
        if tools:
            tool_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in tools.items()])
            prompt = f"""You have access to the following tools:
{tool_descriptions}

User request: {prompt}

Please respond using the appropriate tools.
"""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        if response.startswith(prompt):
            response = response[len(prompt):].strip()
        return response

_llm = None

def get_llm():
    global _llm
    if _llm is None:
        _llm = LocalLLM()
        _llm.load()
    return _llm