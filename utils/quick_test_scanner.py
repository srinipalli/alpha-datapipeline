# quick_test_scanner.py - Test with smaller dataset
from folder_creator import DemoFolderCreator

class QuickTestCreator(DemoFolderCreator):
    def __init__(self):
        super().__init__()
        # Reduce dataset for testing
        self.cicd_tools = ["jenkins", "github_actions"]  # Only 2 tools
        self.projects = ["web-app", "api-service"]       # Only 2 projects
        self.environments = {"dev": 1, "qa": 2}          # Only 2 environments

if __name__ == "__main__":
    creator = QuickTestCreator()
    creator.create_complete_structure()
    print("✅ Quick test structure created (smaller dataset)")
