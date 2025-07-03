# utils/folder_creator.py - Create demo CI/CD folder structure with balanced errors
import os
import random
from datetime import datetime, timedelta

class DemoFolderCreator:
    def __init__(self, base_path="demo_cicd_logs"):
        self.base_path = base_path
        self.cicd_tools = ["jenkins", "github_actions", "gitlab_ci", "azure_devops", "circleci"]
        self.projects = ["web-app", "api-service", "mobile-app", "data-pipeline", "ml-service"]
        self.environments = {
            "dev": 1,
            "qa": 3,
            "stage": 7,
            "production": 10
        }
        self.log_types = ["build", "git_checkout", "test", "sonarqube", "deployment"]
        
        # Balanced error/success ratio for testing
        self.error_probability = 0.5  # 50% error, 50% success
    
    def create_complete_structure(self):
        """Create complete demo folder structure with balanced logs"""
        print("🏗️ Creating demo CI/CD folder structure with balanced errors/success...")
        
        total_files = 0
        error_files = 0
        success_files = 0
        
        for tool in self.cicd_tools:
            for project in self.projects:
                for env, server_count in self.environments.items():
                    for server_num in range(1, server_count + 1):
                        server_path = os.path.join(
                            self.base_path, tool, project, env, f"server_{server_num}"
                        )
                        os.makedirs(server_path, exist_ok=True)
                        
                        # Create balanced error/success logs
                        files_created, errors_created = self.create_balanced_logs(
                            server_path, tool, project, env, server_num
                        )
                        total_files += files_created
                        error_files += errors_created
                        success_files += (files_created - errors_created)
        
        print(f"✅ Created demo structure at {self.base_path}")
        print(f"📊 Statistics:")
        print(f"   Total files: {total_files}")
        print(f"   Error logs: {error_files} ({error_files/total_files*100:.1f}%)")
        print(f"   Success logs: {success_files} ({success_files/total_files*100:.1f}%)")
        print(f"   Tools: {len(self.cicd_tools)} × Projects: {len(self.projects)} × Environments: 4")
    
    def create_balanced_logs(self, server_path, tool, project, env, server_num):
        """Create balanced error/success log files"""
        files_created = 0
        errors_created = 0
        
        for log_type in self.log_types:
            # Determine if this should be an error or success
            has_error = random.random() < self.error_probability
            
            log_content = self.generate_realistic_log_content(
                tool, project, env, server_num, log_type, has_error
            )
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            status = "error" if has_error else "success"
            log_filename = f"{log_type}_{status}_{timestamp}.log"
            log_filepath = os.path.join(server_path, log_filename)
            
            with open(log_filepath, 'w') as f:
                f.write(log_content)
            
            files_created += 1
            if has_error:
                errors_created += 1
        
        return files_created, errors_created
    
    def generate_realistic_log_content(self, tool, project, env, server_num, log_type, has_error):
        """Generate realistic log content based on type and error status"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_templates = {
            "build": self.generate_build_log(timestamp, tool, project, env, server_num, has_error),
            "git_checkout": self.generate_git_log(timestamp, tool, project, env, server_num, has_error),
            "test": self.generate_test_log(timestamp, tool, project, env, server_num, has_error),
            "sonarqube": self.generate_sonar_log(timestamp, tool, project, env, server_num, has_error),
            "deployment": self.generate_deployment_log(timestamp, tool, project, env, server_num, has_error)
        }
        
        return log_templates.get(log_type, f"[{timestamp}] INFO: Generic log for {log_type}")
    
    def generate_build_log(self, timestamp, tool, project, env, server_num, has_error):
        """Generate realistic build logs"""
        if has_error:
            error_scenarios = [
                f"""[{timestamp}] INFO: Starting build for {project} on {tool}
[{timestamp}] INFO: Environment: {env}, Server: {server_num}
[{timestamp}] INFO: Downloading dependencies...
[{timestamp}] INFO: Node.js version: 18.17.0
[{timestamp}] INFO: npm version: 9.6.7
[{timestamp}] INFO: Installing packages...
[{timestamp}] ERROR: Build failed - missing dependency 'react-scripts'
[{timestamp}] ERROR: npm ERR! code ELIFECYCLE
[{timestamp}] ERROR: npm ERR! errno 1
[{timestamp}] ERROR: Exit code: 1
[{timestamp}] FATAL: Build process terminated
[{timestamp}] ERROR: Build duration: 2m 45s""",
                
                f"""[{timestamp}] INFO: Starting Maven build for {project}
[{timestamp}] INFO: Environment: {env}, Server: {server_num}
[{timestamp}] INFO: Java version: 11.0.19
[{timestamp}] INFO: Maven version: 3.8.6
[{timestamp}] INFO: Compiling source code...
[{timestamp}] ERROR: Compilation failure
[{timestamp}] ERROR: [ERROR] /src/main/java/App.java:[15,8] cannot find symbol
[{timestamp}] ERROR: symbol: class InvalidClass
[{timestamp}] ERROR: location: class App
[{timestamp}] FATAL: BUILD FAILURE
[{timestamp}] ERROR: Total time: 1m 23s""",
                
                f"""[{timestamp}] INFO: Docker build started for {project}
[{timestamp}] INFO: Environment: {env}, Server: {server_num}
[{timestamp}] INFO: Building image: {project}:{env}
[{timestamp}] INFO: Step 1/8 : FROM node:18-alpine
[{timestamp}] INFO: Step 2/8 : WORKDIR /app
[{timestamp}] INFO: Step 3/8 : COPY package*.json ./
[{timestamp}] ERROR: Step 4/8 : RUN npm install
[{timestamp}] ERROR: npm ERR! network timeout
[{timestamp}] ERROR: npm ERR! network This is a problem related to network connectivity
[{timestamp}] FATAL: Docker build failed with exit code 1
[{timestamp}] ERROR: Build time: 5m 12s"""
            ]
            return random.choice(error_scenarios)
        else:
            success_scenarios = [
                f"""[{timestamp}] INFO: Starting build for {project} on {tool}
[{timestamp}] INFO: Environment: {env}, Server: {server_num}
[{timestamp}] INFO: Downloading dependencies...
[{timestamp}] INFO: Node.js version: 18.17.0
[{timestamp}] INFO: npm version: 9.6.7
[{timestamp}] INFO: Installing packages...
[{timestamp}] INFO: Dependencies installed successfully (245 packages)
[{timestamp}] INFO: Compiling TypeScript...
[{timestamp}] INFO: TypeScript compilation successful
[{timestamp}] INFO: Running webpack build...
[{timestamp}] INFO: Build completed successfully
[{timestamp}] INFO: Build artifacts created in dist/
[{timestamp}] INFO: Build duration: 1m 32s""",
                
                f"""[{timestamp}] INFO: Maven build started for {project}
[{timestamp}] INFO: Environment: {env}, Server: {server_num}
[{timestamp}] INFO: Java version: 11.0.19
[{timestamp}] INFO: Maven version: 3.8.6
[{timestamp}] INFO: Compiling source code...
[{timestamp}] INFO: Compilation successful (0 errors, 0 warnings)
[{timestamp}] INFO: Running unit tests...
[{timestamp}] INFO: Tests run: 25, Failures: 0, Errors: 0, Skipped: 0
[{timestamp}] INFO: Creating JAR file...
[{timestamp}] INFO: BUILD SUCCESS
[{timestamp}] INFO: Total time: 2m 15s"""
            ]
            return random.choice(success_scenarios)
    
    def generate_git_log(self, timestamp, tool, project, env, server_num, has_error):
        """Generate realistic git checkout logs"""
        if has_error:
            error_scenarios = [
                f"""[{timestamp}] INFO: Git checkout started for {project}
[{timestamp}] INFO: Repository: https://github.com/company/{project}
[{timestamp}] INFO: Branch: {'main' if env == 'production' else 'develop'}
[{timestamp}] INFO: Attempting to clone repository...
[{timestamp}] ERROR: Git checkout failed - authentication error
[{timestamp}] ERROR: remote: Repository not found
[{timestamp}] ERROR: fatal: Authentication failed for repository
[{timestamp}] ERROR: Exit code: 128
[{timestamp}] ERROR: Checkout duration: 45s""",
                
                f"""[{timestamp}] INFO: Git operations for {project}
[{timestamp}] INFO: Repository: https://gitlab.com/company/{project}
[{timestamp}] INFO: Fetching latest changes...
[{timestamp}] ERROR: Git fetch failed
[{timestamp}] ERROR: fatal: unable to access repository
[{timestamp}] ERROR: SSL certificate problem: certificate has expired
[{timestamp}] ERROR: Connection timeout after 30 seconds
[{timestamp}] FATAL: Git operation failed"""
            ]
            return random.choice(error_scenarios)
        else:
            success_scenarios = [
                f"""[{timestamp}] INFO: Git checkout started for {project}
[{timestamp}] INFO: Repository: https://github.com/company/{project}
[{timestamp}] INFO: Branch: {'main' if env == 'production' else 'develop'}
[{timestamp}] INFO: Cloning repository...
[{timestamp}] INFO: Commit: abc123def456
[{timestamp}] INFO: Author: developer@company.com
[{timestamp}] INFO: Message: "Fix user authentication bug"
[{timestamp}] INFO: Files changed: 5 files, +127 -45 lines
[{timestamp}] INFO: Git checkout completed successfully
[{timestamp}] INFO: Checkout duration: 12s""",
                
                f"""[{timestamp}] INFO: Git operations for {project}
[{timestamp}] INFO: Repository: https://gitlab.com/company/{project}
[{timestamp}] INFO: Fetching latest changes...
[{timestamp}] INFO: Fast-forward merge successful
[{timestamp}] INFO: Latest commit: def456abc789
[{timestamp}] INFO: Branch is up to date with origin/develop
[{timestamp}] INFO: Git operations completed successfully"""
            ]
            return random.choice(success_scenarios)
    
    def generate_test_log(self, timestamp, tool, project, env, server_num, has_error):
        """Generate realistic test logs"""
        if has_error:
            error_scenarios = [
                f"""[{timestamp}] INFO: Running test suite for {project}
[{timestamp}] INFO: Environment: {env}
[{timestamp}] INFO: Test framework: Jest
[{timestamp}] INFO: Running unit tests...
[{timestamp}] INFO: Running integration tests...
[{timestamp}] ERROR: Test failed - 3 out of 15 tests failed
[{timestamp}] ERROR: FAIL src/components/Login.test.js
[{timestamp}] ERROR: ✕ should render login form (25ms)
[{timestamp}] ERROR: ✕ should validate email format (15ms)
[{timestamp}] ERROR: ✕ should handle login submission (45ms)
[{timestamp}] ERROR: Test coverage: 65% (below threshold of 80%)
[{timestamp}] FATAL: Test suite failed
[{timestamp}] ERROR: Test duration: 3m 21s""",
                
                f"""[{timestamp}] INFO: PyTest execution for {project}
[{timestamp}] INFO: Environment: {env}
[{timestamp}] INFO: Python version: 3.9.16
[{timestamp}] INFO: Collecting tests...
[{timestamp}] INFO: Found 42 test cases
[{timestamp}] ERROR: FAILED tests/test_api.py::test_user_creation - AssertionError
[{timestamp}] ERROR: FAILED tests/test_database.py::test_connection - ConnectionError
[{timestamp}] ERROR: 2 failed, 40 passed in 2.45s
[{timestamp}] ERROR: Coverage: 72% (below minimum 85%)
[{timestamp}] FATAL: Test execution failed"""
            ]
            return random.choice(error_scenarios)
        else:
            success_scenarios = [
                f"""[{timestamp}] INFO: Running test suite for {project}
[{timestamp}] INFO: Environment: {env}
[{timestamp}] INFO: Test framework: Jest
[{timestamp}] INFO: Running unit tests...
[{timestamp}] INFO: Running integration tests...
[{timestamp}] INFO: All tests passed (15/15)
[{timestamp}] INFO: ✓ Unit tests: 12/12 passed
[{timestamp}] INFO: ✓ Integration tests: 3/3 passed
[{timestamp}] INFO: Test coverage: 92%
[{timestamp}] INFO: Test suite completed successfully
[{timestamp}] INFO: Test duration: 1m 45s""",
                
                f"""[{timestamp}] INFO: PyTest execution for {project}
[{timestamp}] INFO: Environment: {env}
[{timestamp}] INFO: Python version: 3.9.16
[{timestamp}] INFO: Collecting tests...
[{timestamp}] INFO: Found 42 test cases
[{timestamp}] INFO: All tests passed successfully
[{timestamp}] INFO: 42 passed in 1.23s
[{timestamp}] INFO: Coverage: 94%
[{timestamp}] INFO: Test execution completed successfully"""
            ]
            return random.choice(success_scenarios)
    
    def generate_sonar_log(self, timestamp, tool, project, env, server_num, has_error):
        """Generate realistic SonarQube logs"""
        if has_error:
            error_scenarios = [
                f"""[{timestamp}] INFO: SonarQube analysis started for {project}
[{timestamp}] INFO: Quality gate: {env.upper()}
[{timestamp}] INFO: Analyzing code quality...
[{timestamp}] INFO: Lines of code: 15,234
[{timestamp}] ERROR: Quality gate failed - code coverage below 80%
[{timestamp}] ERROR: Code coverage: 65.2%
[{timestamp}] ERROR: Duplicated lines: 8.5%
[{timestamp}] ERROR: Technical debt: 4.2 hours
[{timestamp}] ERROR: Bugs: 12
[{timestamp}] ERROR: Vulnerabilities: 3 (1 high, 2 medium)
[{timestamp}] ERROR: Code smells: 45
[{timestamp}] FATAL: SonarQube quality gate failed
[{timestamp}] ERROR: Analysis duration: 2m 30s""",
                
                f"""[{timestamp}] INFO: SonarQube security scan for {project}
[{timestamp}] INFO: Environment: {env}
[{timestamp}] INFO: Security hotspots analysis...
[{timestamp}] ERROR: Security issues detected
[{timestamp}] ERROR: High severity: SQL injection vulnerability
[{timestamp}] ERROR: Medium severity: Hardcoded credentials found
[{timestamp}] ERROR: Low severity: Weak cryptographic algorithm
[{timestamp}] ERROR: Security rating: E
[{timestamp}] FATAL: Security gate failed"""
            ]
            return random.choice(error_scenarios)
        else:
            success_scenarios = [
                f"""[{timestamp}] INFO: SonarQube analysis started for {project}
[{timestamp}] INFO: Quality gate: {env.upper()}
[{timestamp}] INFO: Analyzing code quality...
[{timestamp}] INFO: Lines of code: 15,234
[{timestamp}] INFO: Code coverage: 87.5%
[{timestamp}] INFO: Duplicated lines: 2.1%
[{timestamp}] INFO: Technical debt: 1.5 hours
[{timestamp}] INFO: Bugs: 0
[{timestamp}] INFO: Vulnerabilities: 0
[{timestamp}] INFO: Code smells: 8 (all minor)
[{timestamp}] INFO: Security rating: A
[{timestamp}] INFO: Quality gate passed
[{timestamp}] INFO: Analysis duration: 1m 45s""",
                
                f"""[{timestamp}] INFO: SonarQube analysis for {project}
[{timestamp}] INFO: Environment: {env}
[{timestamp}] INFO: Code quality metrics:
[{timestamp}] INFO: Maintainability rating: A
[{timestamp}] INFO: Reliability rating: A
[{timestamp}] INFO: Security rating: A
[{timestamp}] INFO: Coverage: 91.2%
[{timestamp}] INFO: All quality gates passed
[{timestamp}] INFO: Analysis completed successfully"""
            ]
            return random.choice(success_scenarios)
    
    def generate_deployment_log(self, timestamp, tool, project, env, server_num, has_error):
        """Generate realistic deployment logs"""
        if has_error:
            error_scenarios = [
                f"""[{timestamp}] INFO: Deployment started for {project}
[{timestamp}] INFO: Target environment: {env}
[{timestamp}] INFO: Server: {server_num}
[{timestamp}] INFO: Deploying to Kubernetes cluster...
[{timestamp}] INFO: Creating namespace: {project}-{env}
[{timestamp}] INFO: Applying deployment manifests...
[{timestamp}] ERROR: Deployment failed - insufficient resources
[{timestamp}] ERROR: Pod {project}-deployment-abc123 failed to start
[{timestamp}] ERROR: ImagePullBackOff: Failed to pull image
[{timestamp}] ERROR: Error: ErrImagePull
[{timestamp}] ERROR: Back-off pulling image "{project}:latest"
[{timestamp}] ERROR: Rollback initiated
[{timestamp}] FATAL: Deployment failed
[{timestamp}] ERROR: Deployment duration: 8m 45s""",
                
                f"""[{timestamp}] INFO: AWS ECS deployment for {project}
[{timestamp}] INFO: Environment: {env}
[{timestamp}] INFO: Task definition: {project}-{env}:15
[{timestamp}] INFO: Starting service update...
[{timestamp}] ERROR: Service update failed
[{timestamp}] ERROR: Task stopped due to: Essential container in task exited
[{timestamp}] ERROR: Exit code: 1
[{timestamp}] ERROR: Health check failed: connection refused
[{timestamp}] ERROR: Rolling back to previous version
[{timestamp}] FATAL: ECS deployment failed"""
            ]
            return random.choice(error_scenarios)
        else:
            success_scenarios = [
                f"""[{timestamp}] INFO: Deployment started for {project}
[{timestamp}] INFO: Target environment: {env}
[{timestamp}] INFO: Server: {server_num}
[{timestamp}] INFO: Deploying to Kubernetes cluster...
[{timestamp}] INFO: Creating namespace: {project}-{env}
[{timestamp}] INFO: Applying deployment manifests...
[{timestamp}] INFO: Deployment created successfully
[{timestamp}] INFO: Pods starting...
[{timestamp}] INFO: Pod {project}-deployment-xyz789 is running
[{timestamp}] INFO: Service created: {project}-service
[{timestamp}] INFO: Ingress configured
[{timestamp}] INFO: Health check passed
[{timestamp}] INFO: Deployment completed successfully
[{timestamp}] INFO: Service available at: https://{project}-{env}.company.com
[{timestamp}] INFO: Deployment duration: 3m 12s""",
                
                f"""[{timestamp}] INFO: AWS ECS deployment for {project}
[{timestamp}] INFO: Environment: {env}
[{timestamp}] INFO: Task definition: {project}-{env}:16
[{timestamp}] INFO: Starting service update...
[{timestamp}] INFO: Service update in progress...
[{timestamp}] INFO: New tasks started successfully
[{timestamp}] INFO: Health checks passing
[{timestamp}] INFO: Old tasks stopped gracefully
[{timestamp}] INFO: Service update completed
[{timestamp}] INFO: ECS deployment successful"""
            ]
            return random.choice(success_scenarios)

if __name__ == "__main__":
    creator = DemoFolderCreator()
    creator.create_complete_structure()
