# evaluation_harness/benchmarks_base.py
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional

# Attempt to import PraxisCore for type hinting if available
try:
    from main import PraxisCore
except ImportError:
    PraxisCore = None # type: ignore

class EvaluationBenchmark(ABC):
    """Abstract base class for all evaluation benchmarks."""
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Benchmark.{self.name}")

    @abstractmethod
    def load_data(self, data_path: Optional[str] = None) -> None:
        """Loads benchmark-specific data."""
        pass

    @abstractmethod
    def run(self, praxis_instance: Optional[PraxisCore] = None, **kwargs) -> Any:
        """
        Executes the benchmark.
        'praxis_instance' is an object/function to interact with Praxis.
        Returns raw results or intermediate data needed for metric calculation.
        """
        pass

    @abstractmethod
    def calculate_metrics(self, run_results: Any) -> Dict[str, Any]:
        """
        Calculates metrics from the raw results of the run method.
        Returns a dictionary of metric_name: value.
        """
        pass

class CIQBenchmarkBase(EvaluationBenchmark):
    """Base class for Cognitive Intelligence Quotient benchmarks."""
    pass

class CEQBenchmarkBase(EvaluationBenchmark):
    """Base class for Cognitive Emotional Quotient benchmarks."""
    pass