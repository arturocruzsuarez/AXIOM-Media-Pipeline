import requests

def publish_to_axiom():
    # --- CONFIGURACIÓN ---
    API_URL = "http://localhost:8000/api/projects/1/upload/"
    # Tu llave maestra generada en Docker
    TOKEN = "2961d308c7d9ea1c289ae641b4534fe08a4efdb1" 
    
    # Datos del Asset (Categoría: COMP)
    payload = {
        "asset_name": "Test_Comp_Asset",
        "department": "COMP" 
    }
    
    # USAMOS 'r' al principio para que Python no se confunda con las diagonales de Windows
    video_path = r"C:\Users\thema\Videos\test_render\test_shot.mp4"

    # --- EJECUCIÓN ---
    headers = {"Authorization": f"Token {TOKEN}"}
    
    try:
        with open(video_path, 'rb') as f:
            files = {'file': f}
            print(f"🚀 Conectando con AXIOM para subir: {payload['asset_name']}...")
            
            response = requests.post(API_URL, headers=headers, data=payload, files=files)
        
        if response.status_code == 201:
            print("✅ ¡Éxito! Versión registrada en el Pipeline.")
            print(f"📡 Respuesta del Servidor: {response.json()['message']}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except FileNotFoundError:
        print(f"💥 Error: No encontré el archivo en {video_path}. Verifica que el nombre sea correcto.")
    except Exception as e:
        print(f"💥 Fallo inesperado: {str(e)}")

if __name__ == "__main__":
    publish_to_axiom()