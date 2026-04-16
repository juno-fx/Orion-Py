"""
Pytest configuration file for orionpy tests.
"""
import os


def pytest_configure(config):
    """Configure test environment."""
    # Set up any required environment variables
    os.environ['TEST_NAMESPACE'] = os.environ.get('TEST_NAMESPACE', 'default')
    os.environ['TEST_SERVICE'] = os.environ.get('TEST_SERVICE', 'test-service')
