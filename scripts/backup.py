"""
Script de backup do banco de dados CSRemote
"""
import os
import subprocess
import datetime
try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    boto3 = None
    HAS_BOTO3 = False
from pathlib import Path

def create_backup():
    """Criar backup do banco PostgreSQL"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"csremote_backup_{timestamp}.sql"
    
    # Configurações do banco
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'user': os.getenv('DB_USER', 'csremote_user'),
        'password': os.getenv('DB_PASSWORD', 'csremote_pass'),
        'database': os.getenv('DB_NAME', 'csremote_db')
    }
    
    # Comando pg_dump
    cmd = [
        'pg_dump',
        f"--host={db_config['host']}",
        f"--port={db_config['port']}",
        f"--username={db_config['user']}",
        f"--dbname={db_config['database']}",
        '--verbose',
        '--clean',
        '--no-owner',
        '--no-privileges',
        f"--file={backup_filename}"
    ]
    
    # Configurar senha via variável de ambiente
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"✅ Backup criado: {backup_filename}")
        return backup_filename
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao criar backup: {e}")
        return None

def upload_to_s3(filename):
    """Upload do backup para S3"""
    if not HAS_BOTO3:
        print("⚠️  Biblioteca 'boto3' não está instalada; pulando upload para S3")
        return False
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.getenv('BACKUP_S3_BUCKET')
        
        if not bucket_name:
            print("⚠️  Bucket S3 não configurado")
            return False
        
        s3_key = f"backups/{filename}"
        s3_client.upload_file(filename, bucket_name, s3_key)
        print(f"✅ Upload para S3: s3://{bucket_name}/{s3_key}")
        
        # Remover arquivo local após upload
        try:
            os.remove(filename)
        except OSError:
            # não interromper se a remoção falhar
            pass
        return True
    except Exception as e:
        print(f"❌ Erro no upload S3: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro no upload S3: {e}")
        return False
        print(f"❌ Erro no upload S3: {e}")
        return False
        return True
        
    except Exception as e:
        print(f"❌ Erro no upload S3: {e}")
        return False

def cleanup_old_backups():
    """Limpar backups antigos (manter apenas últimos 7 dias)"""
    backup_dir = Path(".")
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=7)
    
    for backup_file in backup_dir.glob("csremote_backup_*.sql"):
        if backup_file.stat().st_mtime < cutoff_date.timestamp():
            backup_file.unlink()
            print(f"🗑️  Backup antigo removido: {backup_file}")

if __name__ == "__main__":
    print("🔄 Iniciando backup do CSRemote...")
    
    backup_file = create_backup()
    if backup_file:
        if os.getenv('BACKUP_S3_BUCKET'):
            upload_to_s3(backup_file)
        cleanup_old_backups()
    
    print("✅ Processo de backup concluído!")