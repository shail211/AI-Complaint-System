import json
import os
from datetime import datetime


class FileManager:

    def save_two_json(self, complaints_data, non_complaints_data, base_filename=None):
        """Save two separate JSON files for complaints and non-complaints"""
        if base_filename is None:
            timestamp = datetime.now().strftime("%A_%B_%d_%Y_%H%M%S")
            base_filename = f"facebook_mentions_{timestamp}"

        complaints_file = f"{base_filename}_complaints.json"
        non_complaints_file = f"{base_filename}_non_complaints.json"

        try:
            # Save complaints file
            with open(complaints_file, "w", encoding="utf-8") as f:
                json.dump(complaints_data, f, indent=2, ensure_ascii=False)

            # Save non-complaints file
            with open(non_complaints_file, "w", encoding="utf-8") as f:
                json.dump(non_complaints_data, f, indent=2, ensure_ascii=False)

            print(f"💾 Complaints saved to: {complaints_file}")
            print(f"💾 Non-complaints saved to: {non_complaints_file}")
            print(
                f"📁 Combined size: {(os.path.getsize(complaints_file) + os.path.getsize(non_complaints_file)) / 1024:.1f} KB"
            )

            return complaints_file, non_complaints_file

        except Exception as e:
            print(f"❌ Error saving split JSON files: {str(e)}")
            return None, None

    def save_to_json(self, data, filename=None):
        """Save data to JSON file with preferred date formatting"""
        if filename is None:
            # Using Tuesday, July 22, 2025 format as preferred
            date_str = datetime.now().strftime("%A_%B_%d_%Y_%H%M%S")
            filename = f"facebook_mentions_{date_str}.json"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"💾 Data saved to: {filename}")
            print(f"📁 File size: {os.path.getsize(filename) / 1024:.1f} KB")
            return filename

        except Exception as e:
            print(f"❌ Error saving JSON: {str(e)}")
            return None

    def load_json_data(self, filename):
        """Load previously saved JSON data"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"📂 Loaded data from: {filename}")
            return data
        except Exception as e:
            print(f"❌ Error loading JSON: {str(e)}")
            return None
