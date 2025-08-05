"""
Profiling utilities for performance testing.

This module provides memory usage tracking, CPU profiling,
and resource monitoring capabilities for performance tests.
"""

import psutil
import time
import gc
import sys
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from pathlib import Path
import json


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time."""
    timestamp: float
    rss_bytes: int          # Resident Set Size
    vms_bytes: int          # Virtual Memory Size
    percent: float          # Memory percentage
    available_bytes: int    # Available system memory
    used_bytes: int         # Used system memory
    gc_objects: int         # Number of objects tracked by GC
    gc_generation_0: int    # Gen 0 GC count
    gc_generation_1: int    # Gen 1 GC count
    gc_generation_2: int    # Gen 2 GC count
    
    @property
    def rss_mb(self) -> float:
        """RSS in megabytes."""
        return self.rss_bytes / (1024 * 1024)
    
    @property
    def vms_mb(self) -> float:
        """VMS in megabytes."""
        return self.vms_bytes / (1024 * 1024)
    
    @property
    def available_mb(self) -> float:
        """Available memory in megabytes."""
        return self.available_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class CPUSnapshot:
    """CPU usage snapshot at a point in time."""
    timestamp: float
    cpu_percent: float      # Overall CPU usage percentage
    cpu_count: int          # Number of CPU cores
    load_average: Optional[List[float]]  # Load average (1, 5, 15 min) - Unix only
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class ResourceUsageProfile:
    """Complete resource usage profile for a test run."""
    test_name: str
    start_time: float
    end_time: float
    duration: float
    memory_snapshots: List[MemorySnapshot]
    cpu_snapshots: List[CPUSnapshot]
    peak_memory_mb: float
    average_memory_mb: float
    memory_delta_mb: float  # Memory change from start to end
    average_cpu_percent: float
    peak_cpu_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'test_name': self.test_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'memory_snapshots': [s.to_dict() for s in self.memory_snapshots],
            'cpu_snapshots': [s.to_dict() for s in self.cpu_snapshots],
            'peak_memory_mb': self.peak_memory_mb,
            'average_memory_mb': self.average_memory_mb,
            'memory_delta_mb': self.memory_delta_mb,
            'average_cpu_percent': self.average_cpu_percent,
            'peak_cpu_percent': self.peak_cpu_percent
        }


class MemoryProfiler:
    """Memory usage profiler for performance testing."""
    
    def __init__(self, sampling_interval: float = 0.1):
        """
        Initialize memory profiler.
        
        Args:
            sampling_interval: Interval between memory snapshots in seconds
        """
        self.sampling_interval = sampling_interval
        self.process = psutil.Process()
        self.snapshots: List[MemorySnapshot] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
    
    def get_current_snapshot(self) -> MemorySnapshot:
        """Get current memory usage snapshot."""
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            virtual_memory = psutil.virtual_memory()
            gc_stats = gc.get_stats()
            
            return MemorySnapshot(
                timestamp=time.time(),
                rss_bytes=memory_info.rss,
                vms_bytes=memory_info.vms,
                percent=memory_percent,
                available_bytes=virtual_memory.available,
                used_bytes=virtual_memory.used,
                gc_objects=len(gc.get_objects()),
                gc_generation_0=gc_stats[0]['collections'] if gc_stats else 0,
                gc_generation_1=gc_stats[1]['collections'] if len(gc_stats) > 1 else 0,
                gc_generation_2=gc_stats[2]['collections'] if len(gc_stats) > 2 else 0
            )
        except Exception as e:
            # Fallback snapshot in case of errors
            return MemorySnapshot(
                timestamp=time.time(),
                rss_bytes=0, vms_bytes=0, percent=0.0,
                available_bytes=0, used_bytes=0, gc_objects=0,
                gc_generation_0=0, gc_generation_1=0, gc_generation_2=0
            )
    
    def start_monitoring(self):
        """Start continuous memory monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.snapshots.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> List[MemorySnapshot]:
        """
        Stop monitoring and return collected snapshots.
        
        Returns:
            List of memory snapshots collected during monitoring
        """
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        return self.snapshots.copy()
    
    @contextmanager
    def profile_memory(self, test_name: str = "test"):
        """
        Context manager for memory profiling.
        
        Args:
            test_name: Name of the test being profiled
            
        Yields:
            Dictionary that will contain profiling results
        """
        start_snapshot = self.get_current_snapshot()
        self.start_monitoring()
        
        profile_result = {'test_name': test_name}
        
        try:
            yield profile_result
        finally:
            snapshots = self.stop_monitoring()
            end_snapshot = self.get_current_snapshot()
            
            # Calculate statistics
            if snapshots:
                memory_values = [s.rss_mb for s in snapshots]
                peak_memory = max(memory_values)
                average_memory = sum(memory_values) / len(memory_values)
            else:
                peak_memory = end_snapshot.rss_mb
                average_memory = end_snapshot.rss_mb
            
            memory_delta = end_snapshot.rss_mb - start_snapshot.rss_mb
            
            profile_result.update({
                'start_memory_mb': start_snapshot.rss_mb,
                'end_memory_mb': end_snapshot.rss_mb,
                'peak_memory_mb': peak_memory,
                'average_memory_mb': average_memory,
                'memory_delta_mb': memory_delta,
                'snapshots_count': len(snapshots),
                'duration': end_snapshot.timestamp - start_snapshot.timestamp
            })
    
    def _monitor_loop(self):
        """Internal monitoring loop."""
        while self.monitoring:
            snapshot = self.get_current_snapshot()
            self.snapshots.append(snapshot)
            time.sleep(self.sampling_interval)
    
    def detect_memory_leaks(self, snapshots: List[MemorySnapshot], 
                          threshold_mb: float = 10.0) -> Dict[str, Any]:
        """
        Detect potential memory leaks from snapshots.
        
        Args:
            snapshots: List of memory snapshots
            threshold_mb: Memory increase threshold to consider a leak
            
        Returns:
            Dictionary with leak analysis
        """
        if len(snapshots) < 10:
            return {'error': 'Need at least 10 snapshots for leak detection'}
        
        # Calculate trend in memory usage
        memory_values = [s.rss_mb for s in snapshots]
        timestamps = [s.timestamp for s in snapshots]
        
        # Simple linear regression to detect upward trend
        n = len(memory_values)
        sum_x = sum(range(n))
        sum_y = sum(memory_values)
        sum_xy = sum(i * memory_values[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))
        
        if n * sum_x2 - sum_x * sum_x == 0:
            slope = 0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Convert slope to MB per second
        duration = timestamps[-1] - timestamps[0]
        slope_mb_per_sec = slope / (duration / n) if duration > 0 else 0
        
        total_increase = memory_values[-1] - memory_values[0]
        leak_detected = total_increase > threshold_mb and slope_mb_per_sec > 0
        
        return {
            'leak_detected': leak_detected,
            'total_memory_increase_mb': total_increase,
            'slope_mb_per_second': slope_mb_per_sec,
            'threshold_mb': threshold_mb,
            'peak_memory_mb': max(memory_values),
            'start_memory_mb': memory_values[0],
            'end_memory_mb': memory_values[-1],
            'duration_seconds': duration
        }


class CPUProfiler:
    """CPU usage profiler for performance testing."""
    
    def __init__(self, sampling_interval: float = 0.1):
        """
        Initialize CPU profiler.
        
        Args:
            sampling_interval: Interval between CPU snapshots in seconds
        """
        self.sampling_interval = sampling_interval
        self.process = psutil.Process()
        self.snapshots: List[CPUSnapshot] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
    
    def get_current_snapshot(self) -> CPUSnapshot:
        """Get current CPU usage snapshot."""
        try:
            cpu_percent = psutil.cpu_percent()
            cpu_count = psutil.cpu_count()
            
            # Load average is Unix-specific
            load_average = None
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                pass  # Not available on Windows
            
            return CPUSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                cpu_count=cpu_count,
                load_average=load_average
            )
        except Exception:
            return CPUSnapshot(
                timestamp=time.time(),
                cpu_percent=0.0,
                cpu_count=1,
                load_average=None
            )
    
    def start_monitoring(self):
        """Start continuous CPU monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.snapshots.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> List[CPUSnapshot]:
        """
        Stop monitoring and return collected snapshots.
        
        Returns:
            List of CPU snapshots collected during monitoring
        """
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        return self.snapshots.copy()
    
    @contextmanager
    def profile_cpu(self, test_name: str = "test"):
        """
        Context manager for CPU profiling.
        
        Args:
            test_name: Name of the test being profiled
            
        Yields:
            Dictionary that will contain profiling results
        """
        start_snapshot = self.get_current_snapshot()
        self.start_monitoring()
        
        profile_result = {'test_name': test_name}
        
        try:
            yield profile_result
        finally:
            snapshots = self.stop_monitoring()
            end_snapshot = self.get_current_snapshot()
            
            # Calculate statistics
            if snapshots:
                cpu_values = [s.cpu_percent for s in snapshots]
                peak_cpu = max(cpu_values)
                average_cpu = sum(cpu_values) / len(cpu_values)
            else:
                peak_cpu = end_snapshot.cpu_percent
                average_cpu = end_snapshot.cpu_percent
            
            profile_result.update({
                'start_cpu_percent': start_snapshot.cpu_percent,
                'end_cpu_percent': end_snapshot.cpu_percent,
                'peak_cpu_percent': peak_cpu,
                'average_cpu_percent': average_cpu,
                'snapshots_count': len(snapshots),
                'duration': end_snapshot.timestamp - start_snapshot.timestamp,
                'cpu_count': end_snapshot.cpu_count
            })
    
    def _monitor_loop(self):
        """Internal monitoring loop."""
        while self.monitoring:
            snapshot = self.get_current_snapshot()
            self.snapshots.append(snapshot)
            time.sleep(self.sampling_interval)


class ResourceProfiler:
    """Combined resource profiler for memory and CPU."""
    
    def __init__(self, sampling_interval: float = 0.1):
        """
        Initialize resource profiler.
        
        Args:
            sampling_interval: Interval between resource snapshots in seconds
        """
        self.memory_profiler = MemoryProfiler(sampling_interval)
        self.cpu_profiler = CPUProfiler(sampling_interval)
    
    @contextmanager
    def profile_resources(self, test_name: str = "test"):
        """
        Context manager for complete resource profiling.
        
        Args:
            test_name: Name of the test being profiled
            
        Yields:
            ResourceUsageProfile object with complete profiling results
        """
        start_time = time.time()
        
        # Start both profilers
        self.memory_profiler.start_monitoring()
        self.cpu_profiler.start_monitoring()
        
        try:
            yield
        finally:
            # Stop profilers and collect data
            memory_snapshots = self.memory_profiler.stop_monitoring()
            cpu_snapshots = self.cpu_profiler.stop_monitoring()
            end_time = time.time()
            
            # Calculate statistics
            if memory_snapshots:
                memory_values = [s.rss_mb for s in memory_snapshots]
                peak_memory = max(memory_values)
                average_memory = sum(memory_values) / len(memory_values)
                memory_delta = memory_snapshots[-1].rss_mb - memory_snapshots[0].rss_mb
            else:
                peak_memory = average_memory = memory_delta = 0.0
            
            if cpu_snapshots:
                cpu_values = [s.cpu_percent for s in cpu_snapshots]
                peak_cpu = max(cpu_values)
                average_cpu = sum(cpu_values) / len(cpu_values)
            else:
                peak_cpu = average_cpu = 0.0
            
            profile = ResourceUsageProfile(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                memory_snapshots=memory_snapshots,
                cpu_snapshots=cpu_snapshots,
                peak_memory_mb=peak_memory,
                average_memory_mb=average_memory,
                memory_delta_mb=memory_delta,
                average_cpu_percent=average_cpu,
                peak_cpu_percent=peak_cpu
            )
            
            yield profile
    
    def save_profile(self, profile: ResourceUsageProfile, filepath: Union[str, Path]):
        """
        Save resource profile to JSON file.
        
        Args:
            profile: ResourceUsageProfile to save
            filepath: Path to save the profile
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)
    
    def load_profile(self, filepath: Union[str, Path]) -> Optional[ResourceUsageProfile]:
        """
        Load resource profile from JSON file.
        
        Args:
            filepath: Path to load the profile from
            
        Returns:
            ResourceUsageProfile object or None if file doesn't exist
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct snapshot objects
        memory_snapshots = [MemorySnapshot(**s) for s in data['memory_snapshots']]
        cpu_snapshots = [CPUSnapshot(**s) for s in data['cpu_snapshots']]
        
        return ResourceUsageProfile(
            test_name=data['test_name'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            duration=data['duration'],
            memory_snapshots=memory_snapshots,
            cpu_snapshots=cpu_snapshots,
            peak_memory_mb=data['peak_memory_mb'],
            average_memory_mb=data['average_memory_mb'],
            memory_delta_mb=data['memory_delta_mb'],
            average_cpu_percent=data['average_cpu_percent'],
            peak_cpu_percent=data['peak_cpu_percent']
        )


def garbage_collect_and_measure() -> Dict[str, Any]:
    """
    Force garbage collection and measure its impact.
    
    Returns:
        Dictionary with garbage collection statistics
    """
    before_objects = len(gc.get_objects())
    before_stats = gc.get_stats()
    
    start_time = time.time()
    collected = gc.collect()
    end_time = time.time()
    
    after_objects = len(gc.get_objects())
    after_stats = gc.get_stats()
    
    return {
        'objects_before': before_objects,
        'objects_after': after_objects,
        'objects_collected': before_objects - after_objects,
        'gc_collected_count': collected,
        'gc_duration': end_time - start_time,
        'gc_stats_before': before_stats,
        'gc_stats_after': after_stats
    }


def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system information for performance context.
    
    Returns:
        Dictionary with system information
    """
    return {
        'python_version': sys.version,
        'platform': sys.platform,
        'cpu_count': psutil.cpu_count(),
        'cpu_count_logical': psutil.cpu_count(logical=True),
        'memory_total_mb': psutil.virtual_memory().total / (1024 * 1024),
        'memory_available_mb': psutil.virtual_memory().available / (1024 * 1024),
        'disk_usage': {
            path: {
                'total_mb': usage.total / (1024 * 1024),
                'free_mb': usage.free / (1024 * 1024)
            }
            for path, usage in [('/', psutil.disk_usage('/'))]
        }
    }