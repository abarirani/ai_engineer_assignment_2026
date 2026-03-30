import json
import threading
from pathlib import Path
from typing import Dict, List
from app.config.settings import StorageSettings


class MemoryService:
    def __init__(self, job_id: str, storage_settings: StorageSettings):
        self._job_id = job_id
        self._storage_settings = storage_settings
        self._memory = []
        self._lock: threading.Lock = threading.Lock()

    def save_edit_attempt(self, tool_call_id: str, prompt: str, input_path: str) -> str:
        """Record a new edit attempt using tool_call_id as edit_id.

        Args:
            tool_call_id: The LangChain tool call ID from ToolRuntime
            prompt: The edit prompt
            input_path: Path to input image

        Returns:
            The tool_call_id used as edit_id
        """
        edit_record = {
            "edit_id": tool_call_id,
            "prompt": prompt,
            "image_path": input_path,
            "evaluation": None,
        }
        with self._lock:
            self._memory.append(edit_record)
        return tool_call_id

    def update_edit_evaluation(self, tool_call_id: str, evaluation: Dict) -> None:
        """Update an existing edit with evaluation results.

        Args:
            tool_call_id: The LangChain tool call ID (used as edit_id)
            evaluation: Dictionary containing score and feedback
        """
        with self._lock:
            for edit in self._memory:
                if edit["edit_id"] == tool_call_id:
                    score = evaluation.get("score")
                    # Convert score to float if it's a string
                    if isinstance(score, str):
                        try:
                            score = float(score)
                        except (ValueError, TypeError):
                            score = 0.0
                    edit["evaluation"] = {
                        "score": score,
                        "feedback": evaluation.get("feedback"),
                    }
                    return
            raise ValueError(f"Edit with tool_call_id {tool_call_id} not found")

    def get_edit_history(self) -> List[Dict]:
        """Retrieve full edit history for the refiner"""
        with self._lock:
            return list(self._memory)

    def dump_to_json(self) -> None:
        """Dump memory to a JSON file.

        Args:
            output_path: Path to the output JSON file.
        """
        with self._lock:
            memory_data = list(self._memory)
        output = Path(self._storage_settings.output_dir) / self._job_id / "memory.json"
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w") as f:
            json.dump(memory_data, f, indent=2)


memory_services: Dict[str, MemoryService] = {}
_memory_services_lock: threading.Lock = threading.Lock()
