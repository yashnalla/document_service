"""
Benchmark utilities for performance testing.

This module provides high-precision timing, statistical analysis,
and performance measurement tools for the performance test suite.
"""

import time
import statistics
import json
import csv
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark."""
    name: str
    iterations: int
    total_time: float
    min_time: float
    max_time: float
    mean_time: float
    median_time: float
    std_dev: float
    percentile_95: float
    percentile_99: float
    operations_per_second: float
    timestamp: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Benchmark: {self.name}\n"
            f"Iterations: {self.iterations}\n"
            f"Mean time: {self.mean_time:.4f}s\n"
            f"Median time: {self.median_time:.4f}s\n"
            f"95th percentile: {self.percentile_95:.4f}s\n"
            f"Std deviation: {self.std_dev:.4f}s\n"
            f"Operations/sec: {self.operations_per_second:.2f}\n"
        )


class PerformanceBenchmark:
    """High-precision performance benchmarking utility."""
    
    def __init__(self, warmup_iterations: int = 3, min_iterations: int = 10):
        """
        Initialize the benchmark utility.
        
        Args:
            warmup_iterations: Number of warmup runs before measurement
            min_iterations: Minimum number of measured iterations
        """
        self.warmup_iterations = warmup_iterations
        self.min_iterations = min_iterations
        self.results_history: List[BenchmarkResult] = []
    
    def benchmark_function(self, func: Callable, iterations: int = None,
                          name: str = None, **kwargs) -> BenchmarkResult:
        """
        Benchmark a function with multiple iterations.
        
        Args:
            func: Function to benchmark
            iterations: Number of iterations (uses min_iterations if None)
            name: Name for the benchmark
            **kwargs: Additional metadata for the benchmark
            
        Returns:
            BenchmarkResult with timing statistics
        """
        if iterations is None:
            iterations = self.min_iterations
        
        if name is None:
            name = func.__name__
        
        # Warmup runs
        for _ in range(self.warmup_iterations):
            try:
                func()
            except Exception:
                pass  # Ignore warmup errors
        
        # Measured runs
        times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            func()
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        # Calculate statistics
        total_time = sum(times)
        min_time = min(times)
        max_time = max(times)
        mean_time = statistics.mean(times)
        median_time = statistics.median(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        
        # Percentiles
        sorted_times = sorted(times)
        percentile_95 = self._percentile(sorted_times, 95)
        percentile_99 = self._percentile(sorted_times, 99)
        
        # Operations per second
        ops_per_sec = iterations / total_time if total_time > 0 else 0
        
        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            mean_time=mean_time,
            median_time=median_time,
            std_dev=std_dev,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            operations_per_second=ops_per_sec,
            timestamp=datetime.now().isoformat(),
            metadata=kwargs
        )
        
        self.results_history.append(result)
        return result
    
    @contextmanager
    def time_context(self, name: str = "operation"):
        """
        Context manager for timing a block of code.
        
        Args:
            name: Name for the timed operation
            
        Yields:
            Dictionary that will contain timing results
        """
        timing_result = {}
        start_time = time.perf_counter()
        
        try:
            yield timing_result
        finally:
            end_time = time.perf_counter()
            timing_result['duration'] = end_time - start_time
            timing_result['name'] = name
            timing_result['timestamp'] = datetime.now().isoformat()
    
    def benchmark_with_setup(self, setup_func: Callable, test_func: Callable,
                           teardown_func: Optional[Callable] = None,
                           iterations: int = None, name: str = None) -> BenchmarkResult:
        """
        Benchmark a function with setup and teardown.
        
        Args:
            setup_func: Function to call before each test iteration
            test_func: Function to benchmark
            teardown_func: Optional function to call after each iteration
            iterations: Number of iterations
            name: Name for the benchmark
            
        Returns:
            BenchmarkResult with timing statistics
        """
        if iterations is None:
            iterations = self.min_iterations
        
        if name is None:
            name = f"{test_func.__name__}_with_setup"
        
        def wrapped_test():
            setup_result = setup_func()
            try:
                if setup_result is not None:
                    test_func(setup_result)
                else:
                    test_func()
            finally:
                if teardown_func:
                    teardown_func(setup_result if setup_result is not None else None)
        
        return self.benchmark_function(wrapped_test, iterations, name)
    
    def compare_benchmarks(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """
        Compare multiple benchmark results.
        
        Args:
            results: List of BenchmarkResult objects to compare
            
        Returns:
            Dictionary with comparison statistics
        """
        if len(results) < 2:
            raise ValueError("Need at least 2 results to compare")
        
        comparison = {
            'fastest': min(results, key=lambda r: r.mean_time),
            'slowest': max(results, key=lambda r: r.mean_time),
            'most_consistent': min(results, key=lambda r: r.std_dev),
            'least_consistent': max(results, key=lambda r: r.std_dev),
            'highest_throughput': max(results, key=lambda r: r.operations_per_second),
            'results_summary': []
        }
        
        baseline = comparison['fastest']
        
        for result in results:
            relative_performance = result.mean_time / baseline.mean_time
            summary = {
                'name': result.name,
                'mean_time': result.mean_time,
                'relative_to_fastest': relative_performance,
                'slower_by_factor': relative_performance,
                'slower_by_percent': (relative_performance - 1) * 100,
                'operations_per_second': result.operations_per_second
            }
            comparison['results_summary'].append(summary)
        
        return comparison
    
    def assert_performance_threshold(self, result: BenchmarkResult, 
                                   max_mean_time: float,
                                   max_percentile_95: Optional[float] = None,
                                   min_ops_per_sec: Optional[float] = None) -> bool:
        """
        Assert that benchmark results meet performance thresholds.
        
        Args:
            result: BenchmarkResult to check
            max_mean_time: Maximum acceptable mean time
            max_percentile_95: Maximum acceptable 95th percentile time
            min_ops_per_sec: Minimum acceptable operations per second
            
        Returns:
            True if all thresholds are met
            
        Raises:
            AssertionError: If any threshold is not met
        """
        errors = []
        
        if result.mean_time > max_mean_time:
            errors.append(
                f"Mean time {result.mean_time:.4f}s exceeds threshold {max_mean_time:.4f}s"
            )
        
        if max_percentile_95 and result.percentile_95 > max_percentile_95:
            errors.append(
                f"95th percentile {result.percentile_95:.4f}s exceeds threshold {max_percentile_95:.4f}s"
            )
        
        if min_ops_per_sec and result.operations_per_second < min_ops_per_sec:
            errors.append(
                f"Operations per second {result.operations_per_second:.2f} below threshold {min_ops_per_sec:.2f}"
            )
        
        if errors:
            error_msg = f"Performance thresholds not met for {result.name}:\n" + "\n".join(errors)
            raise AssertionError(error_msg)
        
        return True
    
    def save_results(self, filepath: Union[str, Path], format: str = "json"):
        """
        Save benchmark results to file.
        
        Args:
            filepath: Path to save results
            format: Output format ("json" or "csv")
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            with open(filepath, 'w') as f:
                json.dump([result.to_dict() for result in self.results_history], 
                         f, indent=2)
        elif format.lower() == "csv":
            if self.results_history:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=self.results_history[0].to_dict().keys())
                    writer.writeheader()
                    for result in self.results_history:
                        writer.writerow(result.to_dict())
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def load_results(self, filepath: Union[str, Path]) -> List[BenchmarkResult]:
        """
        Load benchmark results from file.
        
        Args:
            filepath: Path to load results from
            
        Returns:
            List of BenchmarkResult objects
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        results = []
        for item in data:
            results.append(BenchmarkResult(**item))
        
        return results
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        
        k = (len(data) - 1) * (percentile / 100.0)
        f = int(k)
        c = k - f
        
        if f + 1 < len(data):
            return data[f] * (1 - c) + data[f + 1] * c
        else:
            return data[f]


class PerformanceRegression:
    """Utility for detecting performance regressions."""
    
    def __init__(self, threshold_percent: float = 10.0):
        """
        Initialize regression detector.
        
        Args:
            threshold_percent: Percentage change to consider a regression
        """
        self.threshold_percent = threshold_percent
    
    def detect_regression(self, baseline: BenchmarkResult, 
                         current: BenchmarkResult) -> Dict[str, Any]:
        """
        Detect performance regression between two results.
        
        Args:
            baseline: Baseline benchmark result
            current: Current benchmark result
            
        Returns:
            Dictionary with regression analysis
        """
        mean_change = ((current.mean_time - baseline.mean_time) / baseline.mean_time) * 100
        median_change = ((current.median_time - baseline.median_time) / baseline.median_time) * 100
        p95_change = ((current.percentile_95 - baseline.percentile_95) / baseline.percentile_95) * 100
        
        throughput_change = ((current.operations_per_second - baseline.operations_per_second) 
                           / baseline.operations_per_second) * 100
        
        regression_detected = (
            mean_change > self.threshold_percent or
            median_change > self.threshold_percent or
            p95_change > self.threshold_percent or
            throughput_change < -self.threshold_percent
        )
        
        return {
            'regression_detected': regression_detected,
            'mean_time_change_percent': mean_change,
            'median_time_change_percent': median_change,
            'p95_time_change_percent': p95_change,
            'throughput_change_percent': throughput_change,
            'baseline': baseline.to_dict(),
            'current': current.to_dict(),
            'threshold_percent': self.threshold_percent
        }
    
    def analyze_trend(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """
        Analyze performance trend over multiple results.
        
        Args:
            results: List of BenchmarkResult objects in chronological order
            
        Returns:
            Dictionary with trend analysis
        """
        if len(results) < 3:
            return {'error': 'Need at least 3 results for trend analysis'}
        
        mean_times = [r.mean_time for r in results]
        throughputs = [r.operations_per_second for r in results]
        
        # Simple linear trend calculation
        n = len(mean_times)
        x_values = list(range(n))
        
        # Calculate trend for mean times (positive slope = getting slower)
        time_slope = self._calculate_slope(x_values, mean_times)
        throughput_slope = self._calculate_slope(x_values, throughputs)
        
        # Determine trend direction
        time_trend = "improving" if time_slope < 0 else "degrading" if time_slope > 0 else "stable"
        throughput_trend = "improving" if throughput_slope > 0 else "degrading" if throughput_slope < 0 else "stable"
        
        return {
            'overall_trend': time_trend,
            'time_slope': time_slope,
            'throughput_slope': throughput_slope,
            'time_trend': time_trend,
            'throughput_trend': throughput_trend,
            'data_points': n,
            'latest_vs_earliest': {
                'mean_time_change_percent': ((mean_times[-1] - mean_times[0]) / mean_times[0]) * 100,
                'throughput_change_percent': ((throughputs[-1] - throughputs[0]) / throughputs[0]) * 100
            }
        }
    
    def _calculate_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate slope of linear trend."""
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope


class PerformanceReporter:
    """Generate performance reports from benchmark results."""
    
    def __init__(self):
        """Initialize the performance reporter."""
        pass
    
    def generate_html_report(self, results: List[BenchmarkResult], 
                           output_path: Union[str, Path]) -> None:
        """
        Generate an HTML performance report.
        
        Args:
            results: List of BenchmarkResult objects
            output_path: Path to save the HTML report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html_content = self._generate_html_content(results)
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def _generate_html_content(self, results: List[BenchmarkResult]) -> str:
        """Generate HTML content for the performance report."""
        # Sort results by mean time
        sorted_results = sorted(results, key=lambda r: r.mean_time)
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .fast { background-color: #d4edda; }
        .medium { background-color: #fff3cd; }
        .slow { background-color: #f8d7da; }
        .summary { background-color: #e9ecef; padding: 15px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Performance Test Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Tests:</strong> {total_tests}</p>
        <p><strong>Report Generated:</strong> {timestamp}</p>
        <p><strong>Fastest Test:</strong> {fastest_test} ({fastest_time:.4f}s)</p>
        <p><strong>Slowest Test:</strong> {slowest_test} ({slowest_time:.4f}s)</p>
    </div>
    
    <h2>Detailed Results</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Iterations</th>
            <th>Mean Time (s)</th>
            <th>Median Time (s)</th>
            <th>95th Percentile (s)</th>
            <th>Std Dev (s)</th>
            <th>Ops/Sec</th>
            <th>Status</th>
        </tr>
""".format(
            total_tests=len(results),
            timestamp=datetime.now().isoformat(),
            fastest_test=sorted_results[0].name if results else "N/A",
            fastest_time=sorted_results[0].mean_time if results else 0,
            slowest_test=sorted_results[-1].name if results else "N/A",
            slowest_time=sorted_results[-1].mean_time if results else 0
        )
        
        for result in sorted_results:
            status_class = self._get_status_class(result.mean_time, sorted_results)
            html += f"""
        <tr class="{status_class}">
            <td>{result.name}</td>
            <td>{result.iterations}</td>
            <td>{result.mean_time:.4f}</td>
            <td>{result.median_time:.4f}</td>
            <td>{result.percentile_95:.4f}</td>
            <td>{result.std_dev:.4f}</td>
            <td>{result.operations_per_second:.2f}</td>
            <td>{status_class.title()}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        return html
    
    def _get_status_class(self, mean_time: float, all_results: List[BenchmarkResult]) -> str:
        """Determine status class for HTML coloring."""
        all_times = [r.mean_time for r in all_results]
        min_time = min(all_times)
        max_time = max(all_times)
        
        if mean_time <= min_time + (max_time - min_time) * 0.33:
            return "fast"
        elif mean_time <= min_time + (max_time - min_time) * 0.66:
            return "medium"
        else:
            return "slow"