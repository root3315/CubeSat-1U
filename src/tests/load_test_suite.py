"""
Load Testing Script for CubeSat Communication System
Tests the system under high load conditions
"""
import asyncio
import time
import threading
import json
import struct
import socket
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import matplotlib.pyplot as plt
from datetime import datetime
import os


class CommunicationLoadTester:
    """Load tester for communication system"""
    
    def __init__(self, target_host="localhost", target_port=5000):
        self.target_host = target_host
        self.target_port = target_port
        self.results = {
            'latencies': [],
            'throughput': [],
            'success_rates': [],
            'errors': []
        }
        self.test_start_time = None
        self.test_end_time = None
    
    def generate_telemetry_packet(self):
        """Generate a realistic telemetry packet"""
        packet = bytearray(41)
        packet[0] = 0xAA  # Sync 1
        packet[1] = 0x55  # Sync 2
        packet[2] = 0x01  # Packet type
        struct.pack_into('<H', packet, 3, random.randint(1, 65535))  # Sequence
        struct.pack_into('<I', packet, 5, int(time.time()))  # Timestamp
        struct.pack_into('<f', packet, 9, random.uniform(-1.0, 1.0))  # Mag X
        struct.pack_into('<f', packet, 13, random.uniform(-1.0, 1.0))  # Mag Y
        struct.pack_into('<f', packet, 17, random.uniform(-1.0, 1.0))  # Mag Z
        struct.pack_into('<H', packet, 21, random.randint(0, 65535))  # Corrosion
        struct.pack_into('<I', packet, 23, random.randint(0, 4294967295))  # Radiation
        struct.pack_into('<f', packet, 27, random.uniform(0.0, 50.0))  # Temp
        struct.pack_into('<f', packet, 31, random.uniform(900.0, 1100.0))  # Pressure
        struct.pack_into('<f', packet, 35, random.uniform(0.0, 100.0))  # Humidity
        struct.pack_into('<H', packet, 39, int(random.uniform(3000, 4200)))  # Voltage (mV)
        
        return packet
    
    def send_single_packet(self):
        """Send a single packet and measure response"""
        start_time = time.time()
        
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)  # 5 second timeout
            
            # Generate and send packet
            packet = self.generate_telemetry_packet()
            sock.sendto(packet, (self.target_host, self.target_port))
            
            # Measure latency
            latency = time.time() - start_time
            self.results['latencies'].append(latency)
            
            sock.close()
            return True, latency
            
        except Exception as e:
            error_time = time.time() - start_time
            self.results['errors'].append(str(e))
            self.results['latencies'].append(error_time)  # Record error time as latency
            return False, error_time
    
    def run_concurrent_test(self, num_clients=10, requests_per_client=100):
        """Run test with multiple concurrent clients"""
        print(f"Running load test: {num_clients} clients x {requests_per_client} requests each")
        
        start_time = time.time()
        self.test_start_time = start_time
        
        # Create thread pool
        with ThreadPoolExecutor(max_workers=num_clients) as executor:
            # Submit tasks
            futures = []
            for client_id in range(num_clients):
                for req_id in range(requests_per_client):
                    future = executor.submit(self.send_single_packet)
                    futures.append(future)
            
            # Collect results
            successful_requests = 0
            total_requests = len(futures)
            
            for future in as_completed(futures):
                success, latency = future.result()
                if success:
                    successful_requests += 1
        
        end_time = time.time()
        self.test_end_time = end_time
        
        # Calculate metrics
        duration = end_time - start_time
        total_requests = num_clients * requests_per_client
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        avg_latency = statistics.mean(self.results['latencies']) if self.results['latencies'] else 0
        throughput = total_requests / duration if duration > 0 else 0
        
        # Store results
        self.results['throughput'].append(throughput)
        self.results['success_rates'].append(success_rate)
        
        print(f"\nLoad Test Results:")
        print(f"Duration: {duration:.2f}s")
        print(f"Total Requests: {total_requests}")
        print(f"Successful Requests: {successful_requests}")
        print(f"Success Rate: {success_rate:.2%}")
        print(f"Average Latency: {avg_latency:.4f}s")
        print(f"Throughput: {throughput:.2f} requests/sec")
        print(f"Errors: {len(self.results['errors'])}")
        
        return {
            'duration': duration,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': success_rate,
            'avg_latency': avg_latency,
            'throughput': throughput,
            'error_count': len(self.results['errors'])
        }
    
    def run_ramp_up_test(self, max_clients=50, step_size=5, requests_per_client=50):
        """Run test with gradually increasing load"""
        print(f"Running ramp-up test: up to {max_clients} clients in steps of {step_size}")
        
        results = []
        
        for num_clients in range(step_size, max_clients + 1, step_size):
            print(f"\nTesting with {num_clients} clients...")
            
            # Clear previous results for this step
            self.results['latencies'] = []
            self.results['errors'] = []
            
            # Run test with current number of clients
            result = self.run_concurrent_test(num_clients, requests_per_client)
            result['num_clients'] = num_clients
            results.append(result)
            
            # Brief pause between steps
            time.sleep(2)
        
        return results
    
    def generate_report(self):
        """Generate a detailed test report"""
        report = []
        report.append("=" * 80)
        report.append("CUBESAT COMMUNICATION SYSTEM - LOAD TEST REPORT")
        report.append("=" * 80)
        report.append(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Target: {self.target_host}:{self.target_port}")
        report.append("")
        
        if self.results['latencies']:
            report.append("PERFORMANCE METRICS")
            report.append("-" * 40)
            report.append(f"Total Requests: {len(self.results['latencies'])}")
            report.append(f"Successful: {len(self.results['latencies']) - len(self.results['errors'])}")
            report.append(f"Failed: {len(self.results['errors'])}")
            report.append(f"Success Rate: {(len(self.results['latencies']) - len(self.results['errors'])) / len(self.results['latencies']):.2%}")
            report.append(f"Average Latency: {statistics.mean(self.results['latencies']):.4f}s")
            report.append(f"Median Latency: {statistics.median(self.results['latencies']):.4f}s")
            if len(self.results['latencies']) > 1:
                report.append(f"Latency Std Dev: {statistics.stdev(self.results['latencies']):.4f}s")
            report.append(f"Min Latency: {min(self.results['latencies']):.4f}s")
            report.append(f"Max Latency: {max(self.results['latencies']):.4f}s")
            report.append("")
        
        if self.results['throughput']:
            report.append("THROUGHPUT ANALYSIS")
            report.append("-" * 40)
            report.append(f"Peak Throughput: {max(self.results['throughput']):.2f} req/sec")
            report.append(f"Average Throughput: {statistics.mean(self.results['throughput']):.2f} req/sec")
            report.append("")
        
        if self.results['errors']:
            report.append("ERROR ANALYSIS")
            report.append("-" * 40)
            error_types = {}
            for error in self.results['errors']:
                error_types[error] = error_types.get(error, 0) + 1
            
            for error, count in error_types.items():
                report.append(f"{error}: {count} occurrences")
            report.append("")
        
        report.append("=" * 80)
        
        # Save report
        report_content = "\n".join(report)
        filename = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w") as f:
            f.write(report_content)
        
        print(f"\nDetailed report saved to: {filename}")
        return filename
    
    def plot_results(self, ramp_up_results=None):
        """Plot test results"""
        if not self.results['latencies']:
            print("No latency data to plot")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot 1: Latency distribution
        ax1.hist(self.results['latencies'], bins=50, edgecolor='black')
        ax1.set_title('Latency Distribution')
        ax1.set_xlabel('Latency (seconds)')
        ax1.set_ylabel('Frequency')
        
        # Plot 2: Cumulative latency
        sorted_latencies = sorted(self.results['latencies'])
        cumulative = [i/len(sorted_latencies) for i in range(1, len(sorted_latencies)+1)]
        ax2.plot(sorted_latencies, cumulative)
        ax2.set_title('Cumulative Latency Distribution')
        ax2.set_xlabel('Latency (seconds)')
        ax2.set_ylabel('Cumulative Probability')
        
        # Plot 3: Success rate over time (if we have ramp-up data)
        if ramp_up_results:
            clients = [r['num_clients'] for r in ramp_up_results]
            success_rates = [r['success_rate'] for r in ramp_up_results]
            throughputs = [r['throughput'] for r in ramp_up_results]
            
            ax3.plot(clients, success_rates, marker='o', label='Success Rate')
            ax3.set_title('Success Rate vs Number of Clients')
            ax3.set_xlabel('Number of Concurrent Clients')
            ax3.set_ylabel('Success Rate')
            ax3.grid(True)
            
            ax4.plot(clients, throughputs, marker='s', color='orange', label='Throughput')
            ax4.set_title('Throughput vs Number of Clients')
            ax4.set_xlabel('Number of Concurrent Clients')
            ax4.set_ylabel('Throughput (req/sec)')
            ax4.grid(True)
        else:
            # Just show basic stats if no ramp-up data
            ax3.text(0.5, 0.5, f'Avg Latency: {statistics.mean(self.results["latencies"]):.4f}s\nTotal Requests: {len(self.results["latencies"])}', 
                     horizontalalignment='center', verticalalignment='center', transform=ax3.transAxes, fontsize=14)
            ax3.set_title('Test Summary')
            ax3.axis('off')
            
            ax4.text(0.5, 0.5, f'Success Rate: {((len(self.results["latencies"]) - len(self.results["errors"])) / len(self.results["latencies"])):.2%}\nErrors: {len(self.results["errors"])}', 
                     horizontalalignment='center', verticalalignment='center', transform=ax4.transAxes, fontsize=14)
            ax4.set_title('Success/Error Summary')
            ax4.axis('off')
        
        plt.tight_layout()
        
        # Save plot
        plot_filename = f"load_test_plots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
        print(f"Plots saved to: {plot_filename}")
        plt.show()


async def run_comprehensive_load_test():
    """Run comprehensive load tests"""
    print("Starting comprehensive load testing for CubeSat communication system...")
    
    # Initialize load tester
    tester = CommunicationLoadTester(target_host="127.0.0.1", target_port=5000)
    
    # Test 1: Baseline test with moderate load
    print("\n1. Running baseline test (10 clients x 50 requests)")
    baseline_result = tester.run_concurrent_test(num_clients=10, requests_per_client=50)
    
    # Test 2: High concurrency test
    print("\n2. Running high concurrency test (25 clients x 40 requests)")
    high_concurrency_result = tester.run_concurrent_test(num_clients=25, requests_per_client=40)
    
    # Test 3: Ramp-up test
    print("\n3. Running ramp-up test")
    ramp_up_results = tester.run_ramp_up_test(max_clients=30, step_size=5, requests_per_client=20)
    
    # Generate report
    print("\n4. Generating test report")
    report_file = tester.generate_report()
    
    # Plot results
    print("\n5. Generating plots")
    tester.plot_results(ramp_up_results)
    
    print(f"\nLoad testing completed. Report saved to: {report_file}")
    
    return {
        'baseline': baseline_result,
        'high_concurrency': high_concurrency_result,
        'ramp_up': ramp_up_results,
        'report_file': report_file
    }


if __name__ == "__main__":
    # Run the comprehensive load test
    results = asyncio.run(run_comprehensive_load_test())
    
    # Print summary
    print("\n" + "="*80)
    print("LOAD TEST SUMMARY")
    print("="*80)
    print(f"Baseline Throughput: {results['baseline']['throughput']:.2f} req/sec")
    print(f"High Concurrency Throughput: {results['high_concurrency']['throughput']:.2f} req/sec")
    print(f"Peak Throughput Achieved: {max(r['throughput'] for r in results['ramp_up']):.2f} req/sec")
    print(f"Worst Success Rate: {min(r['success_rate'] for r in results['ramp_up']):.2%}")
    print(f"Report File: {results['report_file']}")