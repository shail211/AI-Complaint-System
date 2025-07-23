# production_scheduler.py - Production-ready minute scheduler
import time
import os
from datetime import datetime, timedelta
import json
import logging

# Import your main function
from main import main

class ProductionScheduler:
    def __init__(self):
        self.run_count = 0
        self.successful_runs = 0
        self.failed_runs = 0
        self.start_time = datetime.now()
        self.last_success = None
        self.is_production = os.getenv('RENDER') == 'true'
        
        # Setup logging
        log_level = logging.INFO if self.is_production else logging.DEBUG
        logging.basicConfig(level=log_level)
        
    def health_check(self):
        """Generate health status"""
        uptime = datetime.now() - self.start_time
        success_rate = (self.successful_runs / self.run_count * 100) if self.run_count > 0 else 0
        
        return {
            "status": "healthy" if success_rate > 80 else "degraded",
            "uptime_minutes": int(uptime.total_seconds() / 60),
            "total_runs": self.run_count,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": f"{success_rate:.1f}%",
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "environment": "production" if self.is_production else "development"
        }
    
    def run_main_job(self):
        """Execute main() with production monitoring"""
        self.run_count += 1
        current_time = datetime.now()
        formatted_time = current_time.strftime('%A, %B %d, %Y at %I:%M %p IST')
        
        print(f"\n🚀 PRODUCTION RUN #{self.run_count}")
        print(f"⏰ {formatted_time}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Execute your main function
            main()
            
            # Success tracking
            duration = time.time() - start_time
            self.successful_runs += 1
            self.last_success = current_time
            
            print(f"✅ Success! Duration: {duration:.1f}s")
            
            # Log health every 5 runs
            if self.run_count % 5 == 0:
                health = self.health_check()
                print(f"📊 Health: {health['status']} | Success Rate: {health['success_rate']}")
                
        except Exception as e:
            # Failure tracking
            duration = time.time() - start_time
            self.failed_runs += 1
            
            print(f"❌ Failed after {duration:.1f}s")
            print(f"💥 Error: {str(e)}")
            
            # Log concerning failure rates
            if self.failed_runs > 0 and self.run_count > 5:
                failure_rate = (self.failed_runs / self.run_count) * 100
                if failure_rate > 20:
                    print(f"⚠️  WARNING: High failure rate ({failure_rate:.1f}%)")
    
    def start(self):
        """Start production scheduler"""
        env_name = "PRODUCTION" if self.is_production else "DEVELOPMENT"
        start_formatted = self.start_time.strftime('%A, %B %d, %Y at %I:%M %p IST')
        
        print(f"🎯 PRODUCTION FACEBOOK SCHEDULER [{env_name}]")
        print(f"⏰ Started: {start_formatted}")
        print(f"🔄 Executing main() every 60 seconds")
        print(f"💾 Monitoring health and performance")
        print(f"🗄️  Saving to MongoDB + JSON files")
        print("=" * 60)
        
        # Initial run
        self.run_main_job()
        
        # Main scheduler loop
        try:
            while True:
                time.sleep(60)  # Wait exactly 1 minute
                self.run_main_job()
                
        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"💥 Scheduler crashed: {e}")
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown with final stats"""
        uptime = datetime.now() - self.start_time
        health = self.health_check()
        
        print(f"\n🛑 SCHEDULER SHUTDOWN")
        print(f"⏰ Total uptime: {uptime}")
        print(f"📊 Final health status: {json.dumps(health, indent=2)}")
        print(f"👋 Goodbye!")

if __name__ == "__main__":
    scheduler = ProductionScheduler()
    scheduler.start()
