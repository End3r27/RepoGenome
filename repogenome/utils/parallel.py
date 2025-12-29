"""Parallel processing utilities for RepoGenome."""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def get_optimal_workers() -> int:
    """
    Get optimal number of worker processes/threads.

    Returns:
        Number of workers (at least 1)
    """
    cpu_count = multiprocessing.cpu_count()
    # Use number of CPUs, but cap at 8 for I/O bound tasks
    return min(cpu_count, 8) if cpu_count > 1 else 1


def process_files_parallel(
    files: List[Path],
    processor: Callable[[Path], T],
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    chunk_size: Optional[int] = None,
) -> List[T]:
    """
    Process files in parallel with chunked processing for memory efficiency.

    Args:
        files: List of file paths to process
        processor: Function to process each file (Path -> T)
        max_workers: Maximum number of workers (None = auto)
        progress_callback: Optional callback(completed, total) for progress
        chunk_size: Process files in chunks of this size (None = auto based on file count)

    Returns:
        List of results in same order as input files
    """
    if not files:
        return []

    if max_workers is None:
        max_workers = get_optimal_workers()

    # Auto-determine chunk size if not provided
    if chunk_size is None:
        # For large file sets, process in chunks to manage memory
        if len(files) > 1000:
            chunk_size = max(100, len(files) // (max_workers * 2))
        else:
            chunk_size = len(files)  # Process all at once for small sets

    # For small numbers of files, use threads (lower overhead)
    # For many files, use processes (better CPU utilization)
    if len(files) < 10:
        executor_class = ThreadPoolExecutor
    else:
        executor_class = ProcessPoolExecutor

    all_results: List[Optional[T]] = []
    completed = 0

    # Process in chunks
    for chunk_start in range(0, len(files), chunk_size):
        chunk_files = files[chunk_start:chunk_start + chunk_size]
        chunk_results: List[Optional[T]] = [None] * len(chunk_files)

        with executor_class(max_workers=max_workers) as executor:
            # Submit all tasks in this chunk
            future_to_index = {
                executor.submit(processor, file_path): i
                for i, file_path in enumerate(chunk_files)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    chunk_results[index] = future.result()
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, len(files))
                except Exception as e:
                    # Store exception info - caller can handle
                    chunk_results[index] = e  # type: ignore

        all_results.extend(chunk_results)

    # Filter out exceptions (or handle them)
    return [r for r in all_results if r is not None and not isinstance(r, Exception)]


def batch_process(
    items: List[T],
    processor: Callable[[List[T]], R],
    batch_size: int = 100,
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[R]:
    """
    Process items in batches in parallel with progress tracking.

    Args:
        items: List of items to process
        processor: Function to process a batch (List[T] -> R)
        batch_size: Number of items per batch
        max_workers: Maximum number of workers (None = auto)
        progress_callback: Optional callback(completed_batches, total_batches) for progress

    Returns:
        List of results from each batch
    """
    if not items:
        return []

    if max_workers is None:
        max_workers = get_optimal_workers()

    # Create batches
    batches = [
        items[i : i + batch_size] for i in range(0, len(items), batch_size)
    ]

    if len(batches) == 1:
        result = processor(batches[0])
        if progress_callback:
            progress_callback(1, 1)
        return [result]

    results = []
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {
            executor.submit(processor, batch): batch for batch in batches
        }

        for future in as_completed(future_to_batch):
            try:
                results.append(future.result())
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(batches))
            except Exception as e:
                # Handle error - could append error result or skip
                if progress_callback:
                    completed += 1
                    progress_callback(completed, len(batches))
                pass

    return results

