import requests
import json
from base64 import b64encode
from nacl import encoding, public
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde el archivo .env
load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise ValueError("El token de GitHub no está configurado en las variables de entorno.")

# Función para cifrar el secreto
def encrypt_secret(public_key: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")

# Función para obtener la clave pública del repositorio
def get_public_key(owner, repo, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# Función para crear o actualizar un secreto en el repositorio
def create_or_update_secret(owner, repo, secret_name, encrypted_value, key_id, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
    
    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    print(f"URL: {url}")
    print(f"Data: {data}")
    response = requests.put(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    print(f"Se ha creado/actualizado el secreto '{secret_name}'.")

# Función para copiar un secreto a un entorno específico
def copy_secret_to_environment(owner, repo, secret_name, encrypted_value, key_id, headers, env_name):
    url = f"https://api.github.com/repos/{owner}/{repo}/environments/{env_name}/secrets/{secret_name}"
    
    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    print(f"URL: {url}")
    print(f"Data: {data}")
    response = requests.put(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    print(f"Se ha copiado el secreto '{secret_name}' al entorno '{env_name}'.")

# Leer configuración desde un archivo
def read_config_from_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Configuración
config = read_config_from_file("config.json")
owner, repo = config["repo"].split('/')
secrets = config["secrets"]
environment_secrets = config.get("ENVIRONMENT_SECRETS", {})

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# Obtener la clave pública del repositorio
public_key_info = get_public_key(owner, repo, headers)
public_key = public_key_info["key"]
key_id = public_key_info["key_id"]

# Crear o actualizar los secretos en el repositorio principal
print("Procesando secretos generales...")
for secret_name, secret_value in secrets.items():
    encrypted_value = encrypt_secret(public_key, secret_value)
    create_or_update_secret(owner, repo, secret_name, encrypted_value, key_id, headers)

# Copiar secretos a los entornos específicos
for env_name, env_secrets in environment_secrets.items():
    print(f"Copiando secretos al entorno: {env_name}")
    for secret_name, secret_value in env_secrets.items():
        encrypted_value = encrypt_secret(public_key, secret_value)
        try:
            copy_secret_to_environment(owner, repo, secret_name, encrypted_value, key_id, headers, env_name)
        except requests.exceptions.HTTPError as e:
            print(f"Error al copiar el secreto '{secret_name}' al entorno '{env_name}': {e}")

print("Se han creado/actualizado los secretos.")
