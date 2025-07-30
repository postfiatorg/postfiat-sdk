#!/usr/bin/env python
import subprocess
import time
import json
from datetime import datetime
import sys

def get_workflow_runs():
    """Get the latest workflow runs"""
    cmd = [
        "gh", "api", 
        "repos/allenday/pfsdk/actions/runs?per_page=5",
        "--jq", ".workflow_runs[] | {id: .id, name: .name, status: .status, conclusion: .conclusion, created_at: .created_at, html_url: .html_url}"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        runs = []
        for line in result.stdout.strip().split('\n'):
            if line:
                runs.append(json.loads(line))
        return runs
    except subprocess.CalledProcessError as e:
        print(f"Error fetching workflow runs: {e}")
        return []

def monitor_workflows(check_interval=60, max_duration=1800):
    """Monitor workflow status with periodic updates"""
    start_time = time.time()
    last_status = {}
    
    print(f"🔍 Starting CI monitoring at {datetime.now().strftime('%H:%M:%S')}")
    print(f"   Will check every {check_interval}s for up to {max_duration//60} minutes")
    print("-" * 60)
    
    while True:
        current_time = time.time()
        elapsed = current_time - start_time
        
        if elapsed > max_duration:
            print(f"\n⏰ Monitoring timeout reached after {max_duration//60} minutes")
            break
            
        runs = get_workflow_runs()
        
        # Check for status changes
        for run in runs:
            run_id = run['id']
            current_status = f"{run['status']}:{run['conclusion'] or 'pending'}"
            
            if run_id not in last_status or last_status[run_id] != current_status:
                # Status changed
                timestamp = datetime.now().strftime('%H:%M:%S')
                status_icon = "🟡" if run['status'] == "in_progress" else \
                             "✅" if run['conclusion'] == "success" else \
                             "❌" if run['conclusion'] == "failure" else "⏸️"
                
                print(f"[{timestamp}] {status_icon} {run['name']}: {run['status']} " +
                      f"({run['conclusion'] or 'running'})")
                print(f"    → {run['html_url']}")
                
                last_status[run_id] = current_status
        
        # Check if all workflows are complete
        all_complete = all(run['status'] == 'completed' for run in runs[:2])  # Check latest 2
        if all_complete and runs:
            print("\n✨ All recent workflows completed!")
            
            # Summary
            success_count = sum(1 for run in runs[:2] if run['conclusion'] == 'success')
            failure_count = sum(1 for run in runs[:2] if run['conclusion'] == 'failure')
            
            if failure_count > 0:
                print(f"⚠️  {failure_count} workflow(s) failed - may need attention")
            else:
                print(f"🎉 All {success_count} workflow(s) succeeded!")
            break
        
        # Sleep before next check
        time.sleep(check_interval)
        sys.stdout.write(".")
        sys.stdout.flush()
    
    print(f"\n🏁 Monitoring completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    # Default: check every 60 seconds for up to 30 minutes
    monitor_workflows(check_interval=60, max_duration=1800)