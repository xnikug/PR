import pytest
import httpx
import asyncio
import time
from typing import List, Dict
import matplotlib.pyplot as plt
import statistics
import os

# Configuration - detect if running in Docker or locally
if os.getenv("DOCKER_ENV") == "true":
    # Running in Docker
    LEADER_URL = "http://leader:8000"
    FOLLOWER_URLS = [f"http://follower{i}:8000" for i in range(1, 6)]
else:
    # Running locally
    LEADER_URL = "http://localhost:8000"
    FOLLOWER_URLS = [f"http://localhost:{8001+i}" for i in range(5)]


@pytest.mark.asyncio
async def test_basic_write_and_read():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Write to leader
        response = await client.post(
            f"{LEADER_URL}/write",
            json={"key": "test_key", "value": "test_value"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Wait for replication
        await asyncio.sleep(0.5)
        
        # Read from leader
        response = await client.get(f"{LEADER_URL}/read/test_key")
        assert response.status_code == 200
        assert response.json()["value"] == "test_value"
        
        # Read from followers
        for follower_url in FOLLOWER_URLS:
            try:
                response = await client.get(f"{follower_url}/read/test_key")
                if response.status_code == 200:
                    assert response.json()["value"] == "test_value"
            except Exception as e:
                print(f"Could not read from {follower_url}: {e}")


@pytest.mark.asyncio
async def test_concurrent_writes():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Perform 10 concurrent writes to the same key
        tasks = []
        for i in range(10):
            task = client.post(
                f"{LEADER_URL}/write",
                json={"key": "concurrent_key", "value": f"value_{i}"}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All writes should complete
        for response in responses:
            assert response.status_code == 200
        
        # Wait for replication
        await asyncio.sleep(0.5)
        
        # Read final value
        response = await client.get(f"{LEADER_URL}/read/concurrent_key")
        assert response.status_code == 200
        print(f"Final value after concurrent writes: {response.json()['value']}")


@pytest.mark.asyncio
async def test_write_only_on_leader():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{FOLLOWER_URLS[0]}/write",
            json={"key": "test", "value": "test"}
        )
        assert response.status_code == 403


async def perform_write(client: httpx.AsyncClient, key: str, value: str) -> tuple:
    start_time = time.perf_counter()
    response = await client.post(
        f"{LEADER_URL}/write",
        json={"key": key, "value": value}
    )
    latency = (time.perf_counter() - start_time) * 1000  # Convert to ms
    return response, latency


async def check_consistency(client: httpx.AsyncClient, keys: List[str]) -> Dict:
    results = {"leader": {}, "followers": [{} for _ in range(5)]}
    
    # Get leader data
    for key in keys:
        try:
            response = await client.get(f"{LEADER_URL}/read/{key}")
            if response.status_code == 200:
                results["leader"][key] = response.json()["value"]
        except Exception as e:
            print(f"Error reading {key} from leader: {e}")
    
    # Get follower data
    for idx, follower_url in enumerate(FOLLOWER_URLS):
        for key in keys:
            try:
                response = await client.get(f"{follower_url}/read/{key}")
                if response.status_code == 200:
                    results["followers"][idx][key] = response.json()["value"]
            except Exception as e:
                print(f"Error reading {key} from follower {idx}: {e}")
    
    return results


@pytest.mark.asyncio
async def test_performance_analysis():
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # Perform 100 writes (10 keys, 10 writes each) in batches
        keys = [f"perf_key_{i}" for i in range(10)]
        latencies = []
        
        print("Performing 100 writes in batches of 10...")
        
        for batch in range(10):
            tasks = []
            for i in range(10):
                key = keys[i]
                value = f"value_{batch}_{i}"
                tasks.append(perform_write(client, key, value))
            
            results = await asyncio.gather(*tasks)
            
            for response, latency in results:
                if response.status_code == 200:
                    latencies.append(latency)
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        
        print(f"\nLatency Statistics:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Median:  {median_latency:.2f}ms")
        print(f"  Min:     {min_latency:.2f}ms")
        print(f"  Max:     {max_latency:.2f}ms")
        print(f"  P95:     {p95_latency:.2f}ms")
        print(f"  P99:     {p99_latency:.2f}ms")
        
        print("\nWaiting 1 second for replication to complete...")
        await asyncio.sleep(1)
        
        consistency_results = await check_consistency(client, keys)
        
        leader_data = consistency_results["leader"]
        print(f"Leader has {len(leader_data)} keys")
        
        consistent_followers = 0
        total_inconsistencies = 0
        
        # Check each follower
        for idx, follower_data in enumerate(consistency_results["followers"]):
            print(f"\nFollower {idx+1} has {len(follower_data)} keys")
            
            # Check for inconsistencies
            mismatches = []
            for key in leader_data:
                if key not in follower_data:
                    mismatches.append(f"Key {key} missing")
                elif leader_data[key] != follower_data[key]:
                    mismatches.append(
                        f"Key {key}: leader={leader_data[key]}, "
                        f"follower={follower_data[key]}"
                    )
            
            if mismatches:
                print(f"Incosistencies: {len(mismatches)}")
                total_inconsistencies += len(mismatches)
                for mismatch in mismatches[:3]:  # Show first 3
                    print(f"    - {mismatch}")
            else:
                print(f"Consistent with leader")
                consistent_followers += 1
        
        print(f"\nConsistency Summary:")
        print(f"  Consistent followers: {consistent_followers}/5")
        print(f"  Total inconsistencies: {total_inconsistencies}")
        
        # Generate plots
        generate_performance_plots(latencies, consistency_results, keys)
        
        return {
            "avg_latency": avg_latency,
            "median_latency": median_latency,
            "p95_latency": p95_latency,
            "p99_latency": p99_latency,
            "latencies": latencies,
            "consistency": consistency_results,
            "consistent_followers": consistent_followers,
            "total_inconsistencies": total_inconsistencies
        }


def generate_performance_plots(latencies: List[float], consistency_results: Dict, keys: List[str]):
    output_dir = "/app/test-results"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a figure with multiple subplots
    fig = plt.figure(figsize=(16, 10))
    
    # 1. Latency Distribution (Histogram)
    ax1 = plt.subplot(2, 3, 1)
    ax1.hist(latencies, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
    ax1.axvline(statistics.mean(latencies), color='red', linestyle='--', 
                linewidth=2, label=f'Mean: {statistics.mean(latencies):.1f}ms')
    ax1.axvline(statistics.median(latencies), color='green', linestyle='--', 
                linewidth=2, label=f'Median: {statistics.median(latencies):.1f}ms')
    ax1.set_xlabel('Latency (ms)', fontsize=10)
    ax1.set_ylabel('Frequency', fontsize=10)
    ax1.set_title('Latency Distribution', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Latency Over Time
    ax2 = plt.subplot(2, 3, 2)
    ax2.plot(latencies, color='steelblue', linewidth=1, alpha=0.7)
    ax2.axhline(statistics.mean(latencies), color='red', linestyle='--', 
                linewidth=2, alpha=0.7, label='Mean')
    ax2.set_xlabel('Write Operation #', fontsize=10)
    ax2.set_ylabel('Latency (ms)', fontsize=10)
    ax2.set_title('Latency Over Time', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Box Plot
    ax3 = plt.subplot(2, 3, 3)
    box = ax3.boxplot([latencies], labels=['Write Latency'], patch_artist=True)
    box['boxes'][0].set_facecolor('steelblue')
    box['boxes'][0].set_alpha(0.7)
    ax3.set_ylabel('Latency (ms)', fontsize=10)
    ax3.set_title('Latency Box Plot', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Percentile Analysis
    ax4 = plt.subplot(2, 3, 4)
    percentiles = [50, 75, 90, 95, 99]
    percentile_values = [statistics.quantiles(latencies, n=100)[p-1] for p in percentiles]
    bars = ax4.bar([f'P{p}' for p in percentiles], percentile_values, 
                   color='steelblue', edgecolor='black', alpha=0.7)
    ax4.set_ylabel('Latency (ms)', fontsize=10)
    ax4.set_title('Latency Percentiles', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, percentile_values):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}ms', ha='center', va='bottom', fontsize=9)
    
    # 5. Consistency Analysis
    ax5 = plt.subplot(2, 3, 5)
    leader_data = consistency_results["leader"]
    follower_counts = []
    for follower_data in consistency_results["followers"]:
        count = sum(1 for key in keys if key in follower_data and 
                   follower_data.get(key) == leader_data.get(key))
        follower_counts.append(count)
    
    bars = ax5.bar([f'F{i+1}' for i in range(5)], follower_counts, 
                   color='green', edgecolor='black', alpha=0.7)
    ax5.axhline(len(keys), color='red', linestyle='--', linewidth=2, 
                label=f'Expected: {len(keys)}')
    ax5.set_ylabel('# Consistent Keys', fontsize=10)
    ax5.set_xlabel('Follower', fontsize=10)
    ax5.set_title('Data Consistency per Follower', fontsize=12, fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3, axis='y')
    ax5.set_ylim([0, len(keys) + 1])
    
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    stats_data = [
        ['Metric', 'Value'],
        ['Total Writes', f'{len(latencies)}'],
        ['Mean Latency', f'{statistics.mean(latencies):.2f} ms'],
        ['Median Latency', f'{statistics.median(latencies):.2f} ms'],
        ['Min Latency', f'{min(latencies):.2f} ms'],
        ['Max Latency', f'{max(latencies):.2f} ms'],
        ['Std Dev', f'{statistics.stdev(latencies):.2f} ms'],
        ['P95', f'{statistics.quantiles(latencies, n=20)[18]:.2f} ms'],
        ['P99', f'{statistics.quantiles(latencies, n=100)[98]:.2f} ms'],
        ['Consistent Followers', f'{sum(1 for c in follower_counts if c == len(keys))}/5']
    ]
    
    table = ax6.table(cellText=stats_data, cellLoc='left', loc='center',
                     colWidths=[0.6, 0.4])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    for i in range(2):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    for i in range(1, len(stats_data)):
        for j in range(2):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')
    
    ax6.set_title('Performance Summary', fontsize=12, fontweight='bold', pad=20)
    
    # Overall title
    fig.suptitle('Distributed KV Store Performance Analysis', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save the figure
    output_path = os.path.join(output_dir, 'performance_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    print("Run this: pytest test_integration.py -v -s")