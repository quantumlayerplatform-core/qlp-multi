#!/usr/bin/env python3
"""Monitor workflow progress with detailed stats"""

import asyncio
import httpx
import sys
import time
from datetime import datetime

async def monitor_workflow(workflow_id: str):
    """Monitor workflow with detailed progress tracking"""
    
    print(f"\n📊 Monitoring Workflow: {workflow_id}")
    print("=" * 70)
    
    start_time = time.time()
    last_completed = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                # Get temporal status
                response = await client.get(f"http://localhost:8000/workflow/status/{workflow_id}")
                if response.status_code == 200:
                    status_data = response.json()
                    
                    workflow_status = status_data.get('workflow_status', 'UNKNOWN')
                    
                    # Try to get result if available
                    if workflow_status in ['COMPLETED', 'FAILED', 'TERMINATED', 'TIMED_OUT']:
                        # Get the full result
                        result_response = await client.get(f"http://localhost:8000/status/{workflow_id}")
                        if result_response.status_code == 200:
                            result = result_response.json()
                            
                            elapsed = time.time() - start_time
                            
                            print(f"\n{'='*70}")
                            print(f"✅ WORKFLOW COMPLETED")
                            print(f"{'='*70}")
                            
                            print(f"\nStatus: {result.get('status', 'unknown')}")
                            print(f"Total Time: {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)")
                            print(f"Tasks Completed: {result.get('tasks_completed', 0)}/{result.get('tasks_total', 0)}")
                            
                            # Show task details
                            outputs = result.get('outputs', [])
                            if outputs:
                                print(f"\n📋 Task Execution Summary:")
                                
                                # Group by status
                                completed = []
                                failed = []
                                cached = []
                                
                                for output in outputs:
                                    task_id = output.get('task_id', 'unknown')
                                    execution = output.get('execution', {})
                                    status = execution.get('status', 'unknown')
                                    exec_time = execution.get('execution_time', 0)
                                    is_cached = execution.get('metadata', {}).get('cached', False)
                                    
                                    if status == 'completed':
                                        if is_cached:
                                            cached.append((task_id, exec_time))
                                        else:
                                            completed.append((task_id, exec_time))
                                    else:
                                        failed.append(task_id)
                                
                                # Show results
                                if completed:
                                    print(f"\n✅ Completed Tasks ({len(completed)}):")
                                    for task_id, exec_time in sorted(completed, key=lambda x: x[1])[:5]:
                                        print(f"   • {task_id}: {exec_time:.1f}s")
                                    if len(completed) > 5:
                                        print(f"   ... and {len(completed)-5} more")
                                
                                if cached:
                                    print(f"\n💾 Cached Tasks ({len(cached)}):")
                                    for task_id, exec_time in cached[:3]:
                                        print(f"   • {task_id}: {exec_time:.1f}s (from cache)")
                                
                                if failed:
                                    print(f"\n❌ Failed Tasks ({len(failed)}):")
                                    for task_id in failed[:3]:
                                        print(f"   • {task_id}")
                                
                                # Performance metrics
                                print(f"\n📈 Performance Metrics:")
                                
                                total_tasks = len(outputs)
                                cache_rate = (len(cached) / total_tasks * 100) if total_tasks > 0 else 0
                                success_rate = ((len(completed) + len(cached)) / total_tasks * 100) if total_tasks > 0 else 0
                                
                                print(f"   • Success Rate: {success_rate:.1f}%")
                                print(f"   • Cache Hit Rate: {cache_rate:.1f}%")
                                print(f"   • Avg Task Time: {elapsed/total_tasks:.1f}s")
                                
                                # Estimate speedup
                                sequential_time = sum(t[1] for t in completed) + sum(t[1] for t in cached)
                                if sequential_time > 0:
                                    speedup = sequential_time / elapsed
                                    print(f"   • Parallel Speedup: {speedup:.1f}x")
                                    print(f"   • Time Saved: {sequential_time - elapsed:.0f}s ({(sequential_time - elapsed)/60:.1f} min)")
                            
                            # Capsule info
                            if result.get('capsule_id'):
                                print(f"\n📦 Capsule Information:")
                                print(f"   • ID: {result['capsule_id']}")
                                print(f"   • Ready: {'Yes' if result.get('delivery_ready') else 'No'}")
                            
                            break
                    else:
                        # Still running - show simple status
                        elapsed = time.time() - start_time
                        print(f"\r⏳ Status: {workflow_status} | Elapsed: {elapsed:.0f}s ({elapsed/60:.1f}m)", end="", flush=True)
                
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"\n❌ Error monitoring workflow: {e}")
                break

async def main():
    if len(sys.argv) != 2:
        print("Usage: python monitor_workflow.py <workflow_id>")
        sys.exit(1)
    
    workflow_id = sys.argv[1]
    await monitor_workflow(workflow_id)

if __name__ == "__main__":
    asyncio.run(main())