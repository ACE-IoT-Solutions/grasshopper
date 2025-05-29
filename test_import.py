"""Test importing Grasshopper modules."""

try:
    import grasshopper
    print("Successfully imported grasshopper")
    
    from grasshopper import version
    print(f"Using version: {version.__version__}")
    
    from grasshopper import agent
    print("Successfully imported grasshopper.agent")
    
    from grasshopper.agent import Grasshopper
    print("Successfully imported Grasshopper class")
    
    # Basic test to see if we can access class methods
    print("\nTesting Grasshopper class attributes and methods:")
    print(f"Grasshopper.who_is_broadcast exists: {hasattr(Grasshopper, 'who_is_broadcast')}")
    print(f"Grasshopper.configure_server_setup exists: {hasattr(Grasshopper, 'configure_server_setup')}")
    
    print("\nAll tests passed successfully!")
except Exception as e:
    print(f"Error: {e}")