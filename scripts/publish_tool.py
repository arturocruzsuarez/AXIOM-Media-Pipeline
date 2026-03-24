import requests
import argparse
import os

def publish_to_axiom(video_path, asset_name, department, token, api_url):
    # Validar que el archivo exista antes de intentar subirlo
    if not os.path.exists(video_path):
        print(f"❌ Error: The file '{video_path}' does not exist.")
        return

    headers = {"Authorization": f"Token {token}"}
    payload = {
        "asset_name": asset_name,
        "department": department
    }
    
    try:
        with open(video_path, 'rb') as f:
            files = {'file': f}
            print(f"🚀 Connecting to AXIOM... \n📦 Uploading: {asset_name} [{department}]")
            
            response = requests.post(api_url, headers=headers, data=payload, files=files)
        
        if response.status_code == 201:
            print("✅ Success! Version registered in the Pipeline.")
            print(f"📡 Server Response: {response.json().get('message', 'File processed.')}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"💥 Unexpected Failure: {str(e)}")

if __name__ == "__main__":
    # Configuración de argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="AXIOM Pipeline - DCC Publish Tool")
    
    parser.add_argument("--file", required=True, help="Path to the video file to upload")
    parser.add_argument("--asset", required=True, help="Name of the asset (e.g., Batman_Cape)")
    parser.add_argument("--dept", default="COMP", help="Department (ANIM, FX, COMP, etc.)")
    parser.add_argument("--token", required=True, help="Your AXIOM API Token")
    parser.add_argument("--url", default="http://localhost:8000/api/projects/1/upload/", help="API Endpoint")

    args = parser.parse_args()

    publish_to_axiom(args.file, args.asset, args.dept, args.token, args.url)