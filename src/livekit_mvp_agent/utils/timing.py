"""
Performance timing utilities
"""

import time
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class TimingInfo:
    """Information about a timing measurement"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self) -> None:
        """Mark timing as finished"""
        if self.end_time is None:
            self.end_time = time.perf_counter()
            self.duration = self.end_time - self.start_time
    
    def is_finished(self) -> bool:
        """Check if timing is finished"""
        return self.end_time is not None


class PerformanceTimer:
    """
    Performance timing utilities for measuring execution times
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.logger = logging.getLogger(__name__)
        
        # Storage for timing data
        self._active_timings: Dict[str, TimingInfo] = {}
        self._completed_timings: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        
        # Summary statistics
        self._stats: Dict[str, Dict[str, float]] = defaultdict(dict)
    
    def start(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start timing an operation
        
        Args:
            name: Name of the operation
            metadata: Optional metadata to store with timing
            
        Returns:
            Timing ID for later reference
        """
        timing_id = f"{name}_{int(time.time() * 1000000)}"
        
        timing_info = TimingInfo(
            name=name,
            start_time=time.perf_counter(),
            metadata=metadata or {}
        )
        
        self._active_timings[timing_id] = timing_info
        
        self.logger.debug(f"Started timing: {name} (ID: {timing_id})")
        
        return timing_id
    
    def stop(self, timing_id: str) -> Optional[float]:
        """
        Stop timing an operation
        
        Args:
            timing_id: Timing ID returned by start()
            
        Returns:
            Duration in seconds, or None if timing not found
        """
        if timing_id not in self._active_timings:
            self.logger.warning(f"Timing ID not found: {timing_id}")
            return None
        
        # Finish the timing
        timing_info = self._active_timings.pop(timing_id)
        timing_info.finish()
        
        # Store in completed timings
        self._completed_timings[timing_info.name].append(timing_info)
        
        # Update statistics
        self._update_stats(timing_info.name)
        
        self.logger.debug(
            f"Stopped timing: {timing_info.name} "
            f"(Duration: {timing_info.duration:.3f}s)"
        )
        
        return timing_info.duration
    
    @contextmanager
    def measure(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for timing operations
        
        Args:
            name: Name of the operation
            metadata: Optional metadata
            
        Usage:
            with timer.measure("my_operation"):
                # code to time
                pass
        """
        timing_id = self.start(name, metadata)
        try:
            yield
        finally:
            self.stop(timing_id)
    
    def _update_stats(self, name: str) -> None:
        """Update statistics for a timing category"""
        timings = self._completed_timings[name]
        
        if not timings:
            return
        
        durations = [t.duration for t in timings if t.duration is not None]
        
        if not durations:
            return
        
        # Calculate statistics
        self._stats[name] = {
            "count": len(durations),
            "total": sum(durations),
            "mean": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
            "last": durations[-1],
        }
        
        # Calculate percentiles for larger datasets
        if len(durations) >= 10:
            sorted_durations = sorted(durations)
            n = len(sorted_durations)
            
            self._stats[name].update({
                "p50": sorted_durations[n // 2],
                "p90": sorted_durations[int(n * 0.9)],
                "p95": sorted_durations[int(n * 0.95)],
                "p99": sorted_durations[int(n * 0.99)] if n >= 100 else sorted_durations[-1],
            })
    
    def get_stats(self, name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a timing category
        
        Args:
            name: Operation name
            
        Returns:
            Dictionary with statistics or None if no data
        """
        return self._stats.get(name)
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all timing categories"""
        return dict(self._stats)
    
    def get_last_timing(self, name: str) -> Optional[TimingInfo]:
        """
        Get the last completed timing for an operation
        
        Args:
            name: Operation name
            
        Returns:
            Last TimingInfo or None if no data
        """
        timings = self._completed_timings.get(name)
        
        if timings:
            return timings[-1]
        
        return None
    
    def get_last_timings(self) -> Dict[str, float]:
        """
        Get last timing duration for all operations
        
        Returns:
            Dictionary mapping operation names to last duration
        """
        result = {}
        
        for name in self._completed_timings:
            last_timing = self.get_last_timing(name)
            if last_timing and last_timing.duration is not None:
                result[name] = last_timing.duration
        
        return result
    
    def get_recent_timings(
        self, 
        name: str, 
        count: int = 10
    ) -> List[TimingInfo]:
        """
        Get recent timings for an operation
        
        Args:
            name: Operation name
            count: Number of recent timings to return
            
        Returns:
            List of recent TimingInfo objects
        """
        timings = self._completed_timings.get(name, deque())
        
        # Return last 'count' timings
        return list(timings)[-count:]
    
    def clear_stats(self, name: Optional[str] = None) -> None:
        """
        Clear timing statistics
        
        Args:
            name: Operation name to clear, or None for all
        """
        if name:
            if name in self._completed_timings:
                self._completed_timings[name].clear()
            if name in self._stats:
                del self._stats[name]
            
            self.logger.info(f"Cleared stats for: {name}")
        else:
            self._completed_timings.clear()
            self._stats.clear()
            
            self.logger.info("Cleared all timing stats")
    
    def get_summary(self, top_n: int = 10) -> Dict[str, Any]:
        """
        Get a summary of timing performance
        
        Args:
            top_n: Number of top operations to include
            
        Returns:
            Summary dictionary
        """
        summary = {
            "total_operations": len(self._stats),
            "active_timings": len(self._active_timings),
            "operations": {}
        }
        
        # Sort operations by total time
        sorted_ops = sorted(
            self._stats.items(),
            key=lambda x: x[1].get("total", 0),
            reverse=True
        )
        
        for name, stats in sorted_ops[:top_n]:
            summary["operations"][name] = {
                "count": stats.get("count", 0),
                "total_time": stats.get("total", 0),
                "avg_time": stats.get("mean", 0),
                "min_time": stats.get("min", 0),
                "max_time": stats.get("max", 0),
                "last_time": stats.get("last", 0),
            }
            
            # Add percentiles if available
            if "p50" in stats:
                summary["operations"][name].update({
                    "p50": stats["p50"],
                    "p90": stats["p90"],
                    "p95": stats["p95"],
                })
        
        return summary
    
    def log_summary(self, top_n: int = 5) -> None:
        """
        Log a performance summary
        
        Args:
            top_n: Number of top operations to log
        """
        summary = self.get_summary(top_n)
        
        self.logger.info(f"Performance Summary (Top {top_n}):")
        self.logger.info(f"  Total operations: {summary['total_operations']}")
        self.logger.info(f"  Active timings: {summary['active_timings']}")
        
        for name, stats in summary["operations"].items():
            self.logger.info(
                f"  {name}: "
                f"count={stats['count']}, "
                f"total={stats['total_time']:.3f}s, "
                f"avg={stats['avg_time']:.3f}s, "
                f"last={stats['last_time']:.3f}s"
            )
    
    def export_timings(self, name: str) -> List[Dict[str, Any]]:
        """
        Export timing data for analysis
        
        Args:
            name: Operation name
            
        Returns:
            List of timing dictionaries
        """
        timings = self._completed_timings.get(name, [])
        
        return [
            {
                "name": timing.name,
                "start_time": timing.start_time,
                "end_time": timing.end_time,
                "duration": timing.duration,
                "metadata": timing.metadata,
            }
            for timing in timings
        ]


# Global timer instance for convenience
_global_timer: Optional[PerformanceTimer] = None


def get_global_timer() -> PerformanceTimer:
    """Get the global timer instance"""
    global _global_timer
    
    if _global_timer is None:
        _global_timer = PerformanceTimer()
    
    return _global_timer


@contextmanager
def time_operation(name: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Convenience function for timing operations with global timer
    
    Args:
        name: Operation name
        metadata: Optional metadata
    """
    timer = get_global_timer()
    with timer.measure(name, metadata):
        yield


def log_timing_summary(top_n: int = 5) -> None:
    """Log timing summary using global timer"""
    timer = get_global_timer()
    timer.log_summary(top_n)