import os
import uvicorn
from grasshopper.app import create_app

def get_agent_data_path(original_path):
    agent_name = os.path.basename(original_path)
    agent_data = f"{agent_name}.agent-data"
    modified_path = os.path.join(original_path, agent_data)
    return modified_path

def ensure_folders_exist(agent_data_path, folder_names):
    for folder in folder_names:
        folder_path = os.path.join(agent_data_path, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{folder}' created.")
        else:
            print(f"Folder '{folder}' already exists.")

def main():
    # Setup data directories
    current_dir = os.getcwd()
    agent_data_path = get_agent_data_path(current_dir)
    folders = ["ttl", "compare", "network_config"]
    ensure_folders_exist(agent_data_path, folders)
    
    # Create FastAPI application
    app = create_app()
    app.state.agent_data_path = agent_data_path
    
    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()