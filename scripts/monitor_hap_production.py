#!/usr/bin/env python3
"""
HAP Production Monitoring Script
Monitors HAP system health and performance in production
"""

import os
import asyncio
import psycopg2
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import argparse
from tabulate import tabulate
import time

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://qlp_user:password@localhost:5432/qlp_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class HAPMonitor:
    def __init__(self):
        self.db_conn = None
        self.redis_client = None
        
    def connect(self):
        """Establish connections to database and Redis"""
        try:
            self.db_conn = psycopg2.connect(DATABASE_URL)
            self.redis_client = redis.from_url(REDIS_URL)
            print("✓ Connected to database and Redis")
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            raise
    
    def get_violations_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get violations summary for the specified time period"""
        cursor = self.db_conn.cursor()
        
        # Violations by severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count
            FROM hap_violations
            WHERE created_at > NOW() - INTERVAL '%s hours'
            GROUP BY severity
            ORDER BY severity
        """, (hours,))
        
        severity_data = cursor.fetchall()
        
        # Total violations
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM hap_violations
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (hours,))
        
        total = cursor.fetchone()[0]
        
        # Violations by category
        cursor.execute("""
            SELECT unnest(categories) as category, COUNT(*) as count
            FROM hap_violations
            WHERE created_at > NOW() - INTERVAL '%s hours'
            GROUP BY category
            ORDER BY count DESC
        """, (hours,))
        
        category_data = cursor.fetchall()
        
        cursor.close()
        
        return {
            "total": total,
            "by_severity": severity_data,
            "by_category": category_data[:5]  # Top 5 categories
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get HAP performance metrics"""
        cursor = self.db_conn.cursor()
        
        # Average processing time
        cursor.execute("""
            SELECT 
                AVG(processing_time_ms) as avg_time,
                MIN(processing_time_ms) as min_time,
                MAX(processing_time_ms) as max_time,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_time
            FROM (
                SELECT (metadata->>'processing_time_ms')::float as processing_time_ms
                FROM hap_violations
                WHERE created_at > NOW() - INTERVAL '1 hour'
                AND metadata ? 'processing_time_ms'
            ) t
        """)
        
        perf_data = cursor.fetchone()
        cursor.close()
        
        # Redis cache stats
        cache_info = self.redis_client.info()
        cache_keys = len(self.redis_client.keys("hap:*"))
        
        return {
            "avg_processing_ms": round(perf_data[0] or 0, 2),
            "min_processing_ms": round(perf_data[1] or 0, 2),
            "max_processing_ms": round(perf_data[2] or 0, 2),
            "p95_processing_ms": round(perf_data[3] or 0, 2),
            "cache_keys": cache_keys,
            "cache_hit_rate": cache_info.get("keyspace_hits", 0) / max(cache_info.get("keyspace_hits", 0) + cache_info.get("keyspace_misses", 1), 1)
        }
    
    def get_high_risk_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get high risk users"""
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
            SELECT 
                user_id,
                risk_score,
                total_violations,
                critical_violations,
                high_violations,
                last_violation_at
            FROM hap_user_risk_scores
            WHERE risk_score >= 0.5
            ORDER BY risk_score DESC
            LIMIT %s
        """, (limit,))
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "user_id": row[0],
                "risk_score": row[1],
                "total_violations": row[2],
                "critical": row[3],
                "high": row[4],
                "last_violation": row[5].strftime("%Y-%m-%d %H:%M") if row[5] else "N/A"
            })
        
        cursor.close()
        return users
    
    def get_recent_violations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent violations"""
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
            SELECT 
                user_id,
                severity,
                categories,
                explanation,
                created_at
            FROM hap_violations
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        
        violations = []
        for row in cursor.fetchall():
            violations.append({
                "user_id": row[0] or "anonymous",
                "severity": row[1],
                "categories": ", ".join(row[2]) if row[2] else "none",
                "explanation": (row[3][:50] + "...") if row[3] and len(row[3]) > 50 else row[3],
                "time": row[4].strftime("%H:%M:%S")
            })
        
        cursor.close()
        return violations
    
    def display_dashboard(self):
        """Display monitoring dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print("HAP PRODUCTION MONITORING DASHBOARD")
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Violations Summary
        summary = self.get_violations_summary(24)
        print("\n📊 VIOLATIONS (Last 24 Hours)")
        print(f"Total: {summary['total']}")
        
        if summary['by_severity']:
            print("\nBy Severity:")
            severity_table = [[s[0].upper(), s[1]] for s in summary['by_severity']]
            print(tabulate(severity_table, headers=["Severity", "Count"], tablefmt="grid"))
        
        if summary['by_category']:
            print("\nTop Categories:")
            category_table = [[c[0], c[1]] for c in summary['by_category']]
            print(tabulate(category_table, headers=["Category", "Count"], tablefmt="grid"))
        
        # Performance Metrics
        perf = self.get_performance_metrics()
        print("\n⚡ PERFORMANCE METRICS")
        perf_table = [
            ["Avg Processing Time", f"{perf['avg_processing_ms']} ms"],
            ["Min Processing Time", f"{perf['min_processing_ms']} ms"],
            ["Max Processing Time", f"{perf['max_processing_ms']} ms"],
            ["95th Percentile", f"{perf['p95_processing_ms']} ms"],
            ["Cache Keys", perf['cache_keys']],
            ["Cache Hit Rate", f"{perf['cache_hit_rate']:.2%}"]
        ]
        print(tabulate(perf_table, headers=["Metric", "Value"], tablefmt="grid"))
        
        # High Risk Users
        high_risk = self.get_high_risk_users(5)
        if high_risk:
            print("\n⚠️  HIGH RISK USERS")
            risk_headers = ["User ID", "Risk Score", "Total", "Critical", "High", "Last Violation"]
            risk_table = [[u['user_id'], f"{u['risk_score']:.2f}", u['total_violations'], 
                          u['critical'], u['high'], u['last_violation']] for u in high_risk]
            print(tabulate(risk_table, headers=risk_headers, tablefmt="grid"))
        
        # Recent Violations
        recent = self.get_recent_violations(5)
        if recent:
            print("\n🚨 RECENT VIOLATIONS")
            recent_headers = ["Time", "User", "Severity", "Categories", "Explanation"]
            recent_table = [[v['time'], v['user_id'], v['severity'].upper(), 
                           v['categories'], v['explanation']] for v in recent]
            print(tabulate(recent_table, headers=recent_headers, tablefmt="grid"))
        
        print("\n" + "=" * 80)
    
    def generate_report(self, output_file: str = "hap_report.json"):
        """Generate detailed JSON report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary_24h": self.get_violations_summary(24),
            "summary_7d": self.get_violations_summary(168),
            "performance": self.get_performance_metrics(),
            "high_risk_users": self.get_high_risk_users(20),
            "recent_violations": self.get_recent_violations(50)
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✓ Report saved to {output_file}")
    
    def check_alerts(self) -> List[str]:
        """Check for conditions that should trigger alerts"""
        alerts = []
        cursor = self.db_conn.cursor()
        
        # Check for spike in violations
        cursor.execute("""
            SELECT COUNT(*) FROM hap_violations
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)
        recent_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT AVG(hourly_count) FROM (
                SELECT COUNT(*) as hourly_count
                FROM hap_violations
                WHERE created_at > NOW() - INTERVAL '24 hours'
                GROUP BY date_trunc('hour', created_at)
            ) t
        """)
        avg_hourly = cursor.fetchone()[0] or 0
        
        if recent_count > avg_hourly * 2:
            alerts.append(f"⚠️  Violation spike detected: {recent_count} in last hour (avg: {avg_hourly:.1f})")
        
        # Check for critical violations
        cursor.execute("""
            SELECT COUNT(*) FROM hap_violations
            WHERE severity = 'critical' AND created_at > NOW() - INTERVAL '1 hour'
        """)
        critical_count = cursor.fetchone()[0]
        
        if critical_count > 0:
            alerts.append(f"🚨 {critical_count} CRITICAL violations in last hour!")
        
        # Check performance degradation
        perf = self.get_performance_metrics()
        if perf['avg_processing_ms'] > 100:
            alerts.append(f"⚡ Performance degradation: avg {perf['avg_processing_ms']}ms")
        
        cursor.close()
        return alerts
    
    def close(self):
        """Close connections"""
        if self.db_conn:
            self.db_conn.close()
        if self.redis_client:
            self.redis_client.close()


def main():
    parser = argparse.ArgumentParser(description="Monitor HAP system in production")
    parser.add_argument("--watch", action="store_true", help="Continuously monitor (refresh every 30s)")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--alerts", action="store_true", help="Check for alerts only")
    args = parser.parse_args()
    
    monitor = HAPMonitor()
    
    try:
        monitor.connect()
        
        if args.report:
            monitor.generate_report()
        elif args.alerts:
            alerts = monitor.check_alerts()
            if alerts:
                print("\n🚨 ALERTS:")
                for alert in alerts:
                    print(f"  {alert}")
            else:
                print("✓ No alerts")
        elif args.watch:
            print("Starting continuous monitoring (Ctrl+C to stop)...")
            while True:
                monitor.display_dashboard()
                
                # Check alerts
                alerts = monitor.check_alerts()
                if alerts:
                    print("\n🚨 ALERTS:")
                    for alert in alerts:
                        print(f"  {alert}")
                
                time.sleep(30)
        else:
            monitor.display_dashboard()
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        monitor.close()


if __name__ == "__main__":
    main()